import React, { useContext } from 'react';
import { Typography, TextField, Button, Stack, ButtonGroup } from '@mui/material';

import { ToolContext } from '../App';

function ExternalSource() {

    const { setAwaitingResponse, setPendingRefresh } = useContext(ToolContext);

    function handleSubmit(e) {
        // Prevent the browser from reloading the page
        e.preventDefault();

        // Read the form data
        const form = e.target;
        const formData = new FormData(form);

        setAwaitingResponse(true);
        fetch('/add-external-source', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                setAwaitingResponse(false);
                setPendingRefresh(true);
                console.log(data.message); // Success message from the server
            })
            .catch(error => {
                setAwaitingResponse(false);
                console.error('Error:', error);

            });

    };

    return (
        <Stack
            component='form'
            method='post'
            onSubmit={handleSubmit}
            spacing={2}
            alignItems='center'
        >
            <Typography variant='h6'>External Source</Typography>
            <TextField
                name='source_name'
                label='Source name'
                required
            />
            <TextField
                name='source_root'
                label='Source path'
                required
            />
            <ButtonGroup variant='contained' >
                <Button type='reset'>Default</Button>
                <Button type='submit'>Import</Button>
            </ButtonGroup>
        </Stack>
    );
};

export default ExternalSource;