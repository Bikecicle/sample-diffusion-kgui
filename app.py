from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

import os
import torch
import math
from pathlib import Path

from util.util import load_audio, crop_audio
from util.platform import get_torch_device_type
from dance_diffusion.api import RequestHandler, Request, RequestType, ModelType
from diffusion_library.sampler import SamplerType
from diffusion_library.scheduler import SchedulerType

from .kgui.ddkg import DDKnowledgeGraph

PROJECT_DIR = Path("projects")

ARG_TYPES = {
    # General inference
    "sample_rate": int,
    "chunk_size": int,
    "batch_size": int,
    "steps": int,
    "seed": int,
    # Variation
    "noise_level": float,
    "chunk_interval": int,
}

app = Flask(__name__)
CORS(app)

# Init
device_type_accelerator = get_torch_device_type()
device_accelerator = torch.device(device_type_accelerator)
use_autocast = True  # TODO: Make configurable

request_handler = RequestHandler(
    device_accelerator, optimize_memory_use=False, use_autocast=True
)
ddkg = None

# --------------------
#  Project Management
# --------------------


@app.route("/load", methods=["POST"])
def load_project():
    global ddkg
    ddkg = DDKnowledgeGraph(str(PROJECT_DIR / request.form["project_name"]))
    if ddkg:
        project_name = ddkg.root.name
        return jsonify(
            {"message": f"project loaded: {project_name}", "project": project_name}
        )
    return jsonify({"message": "no project loaded"})


# ---------------
#  Data requests
# ---------------


# Sends the current project name
@app.route("/project", methods=["GET"])
def get_project():
    if ddkg is not None:
        return jsonify({"message": "success", "project_name": ddkg.root.name})
    else:
        return jsonify({"message:": "no project selected"})
    
# Lists projects currently in the local save directory
@app.route("/list-projects", methods=["GET"])
def list_projects():
    project_names = []
    for path in PROJECT_DIR.iterdir():
        if path.is_dir(): project_names.append(path.name)
    if len(project_names > 0):
        return jsonify({"message": "success", "project_names": project_names})
    else:
        return jsonify({"message:": "no projects found"})


# Sends lists of type names for samplers and schedulers
@app.route("/sd-types", methods=["GET"])
def get_type_names():
    return jsonify(
        {
            "samplers": [e.value for e in SamplerType],
            "schedulers": [e.value for e in SchedulerType],
        }
    )


# Sends the current graph state
@app.route("/graph", methods=["GET"])
def get_graph():
    if ddkg is not None:
        return jsonify({"message": "success", "graph_data": ddkg.to_json()})
    else:
        return jsonify({"message:": "no project selected"})


# Sends the current graph state
@app.route("/graph-tsne", methods=["GET"])
def get_graph_tsne():
    if ddkg is not None:
        return jsonify({"message": "success", "graph_data": ddkg.to_json("cluster")})
    else:
        return jsonify({"message:": "no project selected"})


# Sends an audio file corresponding to the given name
@app.route("/audio", methods=["GET"])
def get_audio():
    path = (ddkg.root / ddkg.G.nodes[request.args.get("name")]["path"]).resolve()
    return send_file(str(path))


# Copy an audio file to a new folder for easier access
@app.route("/export-single", methods=["POST"])
def export_single():
    ddkg.export_single(
        name=request.form["name"], export_name=request.form["export_name"]
    )
    return jsonify({"message": "success"})


# Copy an audio batch to a new folder for easier access
@app.route("/export-batch", methods=["POST"])
def export_batch():
    ddkg.export_batch(
        name=request.form["name"], export_name=request.form["export_name"]
    )
    return jsonify({"message": "success"})


# -----------------------
#  External data sources
# -----------------------


# Copies a model to the ddkg dir
@app.route("/import-model", methods=["POST"])
def import_model():
    if ddkg.import_model(
        name=request.form["model_name"],
        path=request.form["model_path"],
        chunk_size=int(request.form["chunk_size"]),
        sample_rate=int(request.form["sample_rate"]),
        steps=int(request.form["steps"]),
        copy=False,
    ):
        message = "Model imported successfully"
    else:
        message = f'Model import failed: model id {request.form["name"]}'

    ddkg.save()
    return jsonify({"message": message})


# Adds an external source
@app.route("/add-external-source", methods=["POST"])
def add_source():
    ddkg.add_external_source(request.form["source_name"], request.form["source_root"])
    ddkg.scan_external_source(request.form["source_name"])
    ddkg.update_tsne()
    ddkg.save()
    return jsonify({"message": "success"})


@app.route("/rescan-source", methods=["POST"])
def scan_source():
    ddkg.scan_external_source(request.args.get("name"))
    ddkg.update_tsne()
    ddkg.save()
    return jsonify({"message": "success"})


# -----------------
#  Model Inference
# -----------------


# Handles basic sample-diffusion requests with minimal interference
@app.route("/sd-request", methods=["POST"])
def handle_sd_request():
    # Cast args
    args = {
        k: ARG_TYPES[k](v) if k in ARG_TYPES else v for k, v in request.form.items()
    }

    # Get model parameters from graph by name
    model_node = ddkg.G.nodes[args["model_name"]]
    args["model_path"] = ddkg.root / model_node["path"]
    args["sample_rate"] = model_node["sample_rate"]

    # Load audio source if specified
    audio_source = None
    if args.get("audio_source_name"):
        audio_node = ddkg.G.nodes[args["audio_source_name"]]
        audio_source = load_audio(
            device_accelerator,
            ddkg.root / audio_node["path"],
            model_node["sample_rate"],
        )
        # Duplicate channel if source is mono
        if audio_source.size(0) == 1:
            audio_source = audio_source.repeat(2, 1)
    else:
        args["audio_source_name"] = None

    request_type = RequestType[args["mode"]]

    if request_type == RequestType.Variation and args["split_chunks"] == "true":
        # Split into a sequence of smaller variation runs
        n_chunks = math.ceil(audio_source.size(-1) / args["chunk_interval"])
        # The following could be used to avoid some padding:
        # n_chunks = math.ceil((audio_source.size(1) - args['chunk_size']) / args['chunk_interval']) + 1
        source_chunks = []
        for chunk_index in range(n_chunks):
            chunk = torch.zeros(2, args["chunk_size"], device=device_accelerator)
            start = chunk_index * args["chunk_interval"]
            end = min(start + args["chunk_size"], audio_source.size(-1))
            chunk[:, : end - start] += audio_source[:, start:end]
            source_chunks.append(chunk)
        output_chunks = []
        for chunk_index, chunk in enumerate(source_chunks):
            print(f"Processing chunk {chunk_index + 1}/{len(source_chunks)}")

            # Construct sample diffusion request
            sd_request = Request(
                request_type=request_type,
                model_type=ModelType.DD,
                model_chunk_size=args["chunk_size"],
                model_sample_rate=args["sample_rate"],
                sampler_type=SamplerType[args["sampler_type_name"]],
                sampler_args={"use_tqdm": True},
                scheduler_type=SchedulerType[args["scheduler_type_name"]],
                scheduler_args={
                    "sigma_min": 0.1,  # TODO: make configurable
                    "sigma_max": 50.0,  # TODO: make configurable
                    "rho": 1.0,  # TODO: make configurable
                },
                audio_source=crop_audio(chunk, chunk_size=args["chunk_size"]),
                **args,
            )

            # Get response, then log to ddkg
            output_chunks.append(request_handler.process_request(sd_request).result)

        # Recombine chunks
        output = torch.zeros(
            args["batch_size"], 2, audio_source.size(-1), device=device_accelerator
        )
        overlap = args['chunk_size'] - args["chunk_interval"]
        left_fade = torch.zeros(args["chunk_size"], device=device_accelerator)
        right_fade = torch.zeros(args["chunk_size"], device=device_accelerator)
        if args["crossfade"]:
            left_fade[:overlap] += torch.linspace(0, 1, overlap, device=device_accelerator)
            left_fade[overlap:] += 1
            right_fade[-overlap:] += torch.linspace(1, 0, overlap, device=device_accelerator)
            right_fade[:-overlap] += 1
        else:
            left_fade[:] += 1
            right_fade[: args["chunk_interval"]] += 1
        mask = torch.zeros(args["chunk_size"], device=device_accelerator)
        mask[: args["chunk_interval"]] += 1
        for chunk_index, chunk in enumerate(output_chunks):
            start = chunk_index * args["chunk_interval"]
            end = min(start + args["chunk_size"], output.size(-1))
            if chunk_index > 0:
                chunk *= left_fade
            if chunk_index < len(output_chunks):
                chunk *= right_fade
            output[:, :, start:end] += chunk[:, :, : end - start]

    else:
        if audio_source is not None:
            audio_source = crop_audio(audio_source, chunk_size=args["chunk_size"])
        sd_request = Request(
            request_type=request_type,
            model_type=ModelType.DD,
            model_chunk_size=args["chunk_size"],
            model_sample_rate=args["sample_rate"],
            sampler_type=SamplerType[args["sampler_type_name"]],
            sampler_args={"use_tqdm": True},
            scheduler_type=SchedulerType[args["scheduler_type_name"]],
            scheduler_args={
                "sigma_min": 0.1,  # TODO: make configurable
                "sigma_max": 50.0,  # TODO: make configurable
                "rho": 1.0,  # TODO: make configurable
            },
            audio_source=audio_source,
            **args,
        )

        # Get response, then log to ddkg
        output = request_handler.process_request(sd_request).result

    ddkg.log_inference(output=output, **args)
    ddkg.update_tsne()
    ddkg.save()
    return jsonify({"message": "success"})


# --------------------
#  Graph Modification
# --------------------


@app.route("/update-element", methods=["POST"])
def update_element():
    ddkg.update_element(request.form["name"], dict(request.form))
    ddkg.save()
    return jsonify({"message": "success"})


@app.route("/update-batch", methods=["POST"])
def update_batch():
    ddkg.update_batch(request.form["name"], dict(request.form))
    ddkg.save()
    return jsonify({"message": "success"})


@app.route("/remove-element", methods=["POST"])
def remove_element():
    ddkg.remove_element(request.form["name"])
    ddkg.save()
    return jsonify({"message": "success"})
