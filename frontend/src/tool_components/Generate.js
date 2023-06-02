import React, { useContext, useState } from "react";
import Select from 'react-select';
import './Tools.css';

import { ToolContext } from "../graph_components/KnowledgeGraph";

function Generate() {
    const defaultSampler = 'V_IPLMS';
    const defaultScheduler = 'V_CRASH';

    const { typeNames, toolParams, setAwaitingResponse } = useContext(ToolContext);
    const [selectedSampler, setSelectedSampler] = useState({value: defaultSampler, label: defaultSampler});
    const [selectedScheduler, setSelectedScheduler] = useState({value: defaultScheduler, label: defaultScheduler});

    const samplerOptions = typeNames.samplers.map((value) => ({
        value,
        label: value
    }));
    const schedulerOptions = typeNames.schedulers.map((value) => ({
        value,
        label: value
    }));

    function handleSubmit(e) {
        // Prevent the browser from reloading the page
        e.preventDefault();

        // Read the form data
        const form = e.target;
        const formData = new FormData(form);
        formData.append('mode', 'Generation');
        formData.append('model_name', toolParams.nodeData.name);
        formData.append('model_path', toolParams.nodeData.path);
        formData.append('model_sample_rate', toolParams.nodeData.sample_rate);
        formData.append('model_chunk_size', toolParams.nodeData.chunk_size);
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
            <h2>Generate</h2>
            <form method="post" onSubmit={handleSubmit}>
                Model: {toolParams.nodeData.name}
                <hr />
                Sample rate: {toolParams.nodeData.sample_rate}
                <hr />
                <label>
                    Chunk size:
                    <input name="chunk_size" type="number" defaultValue={toolParams.nodeData.chunk_size} />
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

export default Generate;