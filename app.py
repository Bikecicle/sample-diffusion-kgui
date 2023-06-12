from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

import torch
from pathlib import Path

from util.util import load_audio
from util.platform import get_torch_device_type
from dance_diffusion.api import RequestHandler, Request, RequestType, ModelType
from diffusion_library.sampler import SamplerType
from diffusion_library.scheduler import SchedulerType

from ddkg import DDKnowledgeGraph

DEFAULT_PATH = './data'
DEFAULT_SD_REPO = '../sample-diffusion'

ARG_TYPES = {
    # General inference
    'sample_rate': int,
    'chunk_size': int,
    'batch_size': int,
    'steps': int,
    'seed': int,
    'noise_level': float
}

app = Flask(__name__)
CORS(app)

# Init
device_type_accelerator = get_torch_device_type()
device_accelerator = torch.device(device_type_accelerator)
use_autocast = True  # TODO: Make configurable

request_handler = RequestHandler(device_accelerator, optimize_memory_use=False, use_autocast=True)
ddkg = DDKnowledgeGraph(DEFAULT_PATH)


# ---------------
#  Data requests
# ---------------


# Sends lists of type names for samplers and schedulers
@app.route('/sd-types', methods=['GET'])
def get_type_names():
    return jsonify({
        'samplers': [e.value for e in SamplerType],
        'schedulers': [e.value for e in SchedulerType]
    })


# Sends the current graph state
@app.route('/graph', methods=['GET'])
def get_graph():
    return jsonify(ddkg.to_json())


# Sends an audio file corresponding to the given name
@app.route('/audio', methods=['GET'])
def get_audio():
    path = Path(ddkg.G.nodes[request.args.get('name')]['path']).resolve()
    return send_file(str(path))


# -----------------------
#  External data sources
# -----------------------


# Copies a model to the ddkg dir
@app.route('/import-model', methods=['POST'])
def import_model():
    if ddkg.import_model(
        name=request.form['model_name'],
        path=request.form['model_path'],
        chunk_size=int(request.form['chunk_size']),
        sample_rate=int(request.form['sample_rate']),
        steps=int(request.form['steps']),
        copy=True
    ):
        message = 'Model imported successfully'
    else:
        message = f'Model import failed: model id {request.form["name"]} already exists'
    
    return jsonify({'message': message})

# Copies a model to the ddkg dir
@app.route('/add-external-source', methods=['POST'])
def add_source():
    ddkg.add_external_source(
        request.form['source_name'],
        request.form['source_root']
    )
    ddkg.scan_external_source(
        request.form['source_name']
    )
    return jsonify({'message': 'success'})


# -----------------
#  Model Inference
# -----------------


# Handles basic sample-diffusion requests with minimal interference
@app.route('/sd-request', methods=['POST'])
def handle_sd_request():
    # Cast args
    args = {k : ARG_TYPES[k](v) if k in ARG_TYPES else v for k, v in request.form.items()}

    model_node = ddkg.G.nodes[args['model_name']]
    args['model_path'] = model_node['path']
    args['sample_rate'] = model_node['sample_rate']

    audio_source = None
    if 'audio_source_name' in args:
        audio_node = ddkg.G.nodes[args['audio_source_name']]
        audio_source = load_audio(device_accelerator, audio_node['path'], audio_node['sample_rate'])
    else:
        args['audio_source_name'] = None

    # Construct sample diffusion request
    sd_request = Request(
        request_type=RequestType[args['mode']],
        model_type=ModelType.DD,
        model_chunk_size=args['chunk_size'],
        model_sample_rate=args['sample_rate'],

        sampler_type=SamplerType[args['sampler_type_name']],
        sampler_args={'use_tqdm': True},

        scheduler_type=SchedulerType[args['scheduler_type_name']],
        scheduler_args={
            'sigma_min': 0.1,  # TODO: make configurable
            'sigma_max': 50.0,  # TODO: make configurable
            'rho': 1.0  # TODO: make configurable
        },

        audio_source=audio_source,
        **args
    )

    # Get response, then log to ddkg
    output = request_handler.process_request(sd_request).result
    ddkg.log_inference(
        output=output,
        **args
    )
  
    return jsonify({'message': 'success'})


# --------------------
#  Graph Modification
# --------------------


@app.route('/update-element', methods=['POST'])
def update_element():
    ddkg.update_element(
        request.form['name'],
        dict(request.form)
    )
    return jsonify({'message': 'success'})