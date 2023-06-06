import React, { useContext, useState } from "react";
import Select from 'react-select';
import './Tools.css';

import { ToolContext } from "../graph_components/KnowledgeGraph";

function Variation() {
    const defaultSampler = 'V_IPLMS';
    const defaultScheduler = 'V_CRASH';

    const { typeNames, modelNames, toolParams, setAwaitingResponse } = useContext(ToolContext);
    const [chunkSize, setChunkSize] = useState(toolParams.nodeData.chunk_size || '65536');

    const modelOptions = modelNames.map((value) => ({
        value,
        label: value
    }));
    const samplerOptions = typeNames.samplers.map((value) => ({
        value,
        label: value
    }));
    const schedulerOptions = typeNames.schedulers.map((value) => ({
        value,
        label: value
    }));
    const [selectedModel, setSelectedModel] = useState(modelOptions[0]);
    const [selectedSampler, setSelectedSampler] = useState({value: defaultSampler, label: defaultSampler});
    const [selectedScheduler, setSelectedScheduler] = useState({value: defaultScheduler, label: defaultScheduler});

    function handleSubmit(e) {
        // Prevent the browser from reloading the page
        e.preventDefault();

        // Read the form data
        const form = e.target;
        const formData = new FormData(form);
        formData.append('mode', 'Variation');
        formData.append('audio_source_name', toolParams.nodeData.name)
        formData.append('model_name', selectedModel.value);
        formData.append('sampler_type_name', selectedSampler.value);
        formData.append('scheduler_type_name', selectedScheduler.value);

        setAwaitingResponse(true);
        fetch('http://localhost:5000/sd-request', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                setAwaitingResponse(false);
                console.log(data.message); // Success message from the server
            })
            .catch(error => {
                setAwaitingResponse(false);
                console.error('Error:', error);
            });
    };


    return (
        <div>
            <h2>Variation</h2>
            <form method="post" onSubmit={handleSubmit}>
                Audio Source: {toolParams.nodeData.name}
                <hr />
                <label>
                    Model:
                    <Select
                        options={modelOptions}
                        defaultValue={selectedModel}
                        onChange={setSelectedModel}
                        className="custom-select"
                    />
                </label>
                <hr />
                Sample rate: {toolParams.nodeData.sample_rate}
                <hr />
                <label>
                    Chunk size:
                    <input 
                        name="chunk_size"
                        type="number"
                        value={chunkSize}
                        onChange={(e) => setChunkSize(e.target.value)}
                    />
                </label>
                <hr />
                <label>
                    Batch size:
                    <input name="batch_size" type="number" defaultValue="1" />
                </label>
                <hr />
                <label>
                    Seed:
                    <input name="seed" type="number" defaultValue="0" />
                </label>
                <hr />
                <label>
                    Step count:
                    <input name="steps" type="number" defaultValue="50" />
                </label>
                <hr />
                <label>
                    Noise level:
                    <input name="noise_level" type="number" defaultValue="0.7" />
                </label>
                <hr />
                <label>
                    Sampler:
                    <Select
                        options={samplerOptions}
                        defaultValue={selectedSampler}
                        onChange={setSelectedSampler}
                        className="custom-select"
                    />
                </label>
                <hr />
                <label>
                    Scheduler:
                    <Select
                        options={schedulerOptions}
                        defaultValue={selectedScheduler}
                        onChange={setSelectedScheduler}
                        className="custom-select"
                    />
                </label>
                <hr />
                <button type="reset">Clear</button>
                <button type="submit">Generate</button>
            </form>
        </div>
    );
}

export default Variation;