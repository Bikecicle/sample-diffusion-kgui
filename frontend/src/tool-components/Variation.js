import React, { useContext, useState } from "react";
import {
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  ButtonGroup,
  InputAdornment,
  IconButton,
  FormControlLabel,
  Checkbox,
  Box,
} from "@mui/material";
import { Autorenew } from "@mui/icons-material";

import { ToolContext } from "../App";

function Variation() {
  const defaultSampler = "V_IPLMS";
  const defaultScheduler = "V_CRASH";

  const {
    typeNames,
    nodeNames,
    toolParams,
    hasModel,
    setActiveTool,
    setAwaitingResponse,
    setPendingRefresh,
  } = useContext(ToolContext);
  const [chunkSize, setChunkSize] = useState(
    toolParams.nodeData.chunk_size || 65536
  );
  const [splitChunks, setSplitChunks] = useState(false);
  const [chunkInterval, setChunkInterval] = useState(chunkSize);
  const [crossfade, setCrossfade] = useState(false);
  const [selectedModel, setSelectedModel] = useState(nodeNames.model[0]);
  const [seed, setSeed] = useState(0);
  const [selectedSampler, setSelectedSampler] = useState(defaultSampler);
  const [selectedScheduler, setSelectedScheduler] = useState(defaultScheduler);

  function randomizeSeed() {
    setSeed(Math.floor(Math.random() * 4294967294));
  }

  function handleSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);
    formData.append("mode", "Variation");
    formData.append("audio_source_name", toolParams.nodeData.name);
    formData.append("sample_rate", toolParams.nodeData.sample_rate);
    formData.append("split_chunks", splitChunks);
    formData.append("chunk_interval", chunkInterval);
    formData.append("crossfade", crossfade);
    formData.append("model_name", selectedModel);
    formData.append("seed", seed);
    formData.append("sampler_type_name", selectedSampler);
    formData.append("scheduler_type_name", selectedScheduler);

    setAwaitingResponse(true);
    setActiveTool("default");
    fetch("/sd-request", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        setAwaitingResponse(false);
        setPendingRefresh(true);
        console.log(data.message);
      })
      .catch((error) => {
        setAwaitingResponse(false);
        console.error("Error:", error);
      });
  }

  if (nodeNames.model) {
    return (
      <Stack
        component="form"
        method="post"
        onSubmit={handleSubmit}
        spacing={2}
        alignItems="center"
      >
        <Typography variant="h6">Variation</Typography>
        <TextField
          name="audio_source_name"
          value={toolParams.nodeData.name}
          label="Audio source"
          disabled
        />
        <TextField
          name="sample_rate"
          value={toolParams.nodeData.sample_rate}
          label="Sample rate"
          disabled
        />
        <FormControl>
          <InputLabel>Model</InputLabel>
          <Select
            value={selectedModel}
            onChange={(event) => setSelectedModel(event.target.value)}
          >
            {nodeNames.model.map((option) => (
              <MenuItem value={option}>{option}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          name="chunk_size"
          type="number"
          value={chunkSize}
          onChange={(event) => setChunkSize(event.target.value)}
          label="Chunk size"
          inputProps={{ min: 32768, step: 32768 }}
        />
        <FormControlLabel
          control={
            <Checkbox
              checked={splitChunks}
              onChange={(event) => setSplitChunks(event.target.checked)}
              defaultChecked={false}
            />
          }
          label="Split into chunks"
        />
        {splitChunks && (
          <TextField
            name="chunk_interval"
            type="number"
            value={chunkInterval}
            onChange={(event) => setChunkInterval(event.target.value)}
            label="Chunk interval"
            inputProps={{ min: 0, step: 1 }}
          />
        )}
        {splitChunks && (
          <FormControlLabel
            control={
              <Checkbox
                checked={crossfade}
                onChange={(event) => setCrossfade(event.target.checked)}
                defaultChecked={false}
              />
            }
            label="Crossfade overlaps"
          />
        )}
        <TextField
          name="batch_size"
          type="number"
          defaultValue="8"
          label="Batch size"
          inputProps={{ min: 1 }}
        />
        <TextField
          value={seed}
          onChange={(event) => setSeed(event.target.value)}
          type="number"
          label="Seed"
          inputProps={{ min: 0 }}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  aria-label="randomize"
                  onClick={randomizeSeed}
                  edge="end"
                >
                  <Autorenew />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
        <TextField
          name="steps"
          type="number"
          defaultValue="200"
          label="Step count"
          inputProps={{ min: 1 }}
        />
        <TextField
          name="noise_level"
          type="number"
          defaultValue="0.7"
          label="Noise level"
          inputProps={{ min: 0.0, max: 1.0, step: 0.1 }}
        />
        <FormControl>
          <InputLabel>Sampler</InputLabel>
          <Select
            value={selectedSampler}
            onChange={(event) => setSelectedSampler(event.target.value)}
          >
            {typeNames.samplers.map((option) => (
              <MenuItem value={option}>{option}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl>
          <InputLabel>Scheduler</InputLabel>
          <Select
            value={selectedScheduler}
            onChange={(event) => setSelectedScheduler(event.target.value)}
          >
            {typeNames.schedulers.map((option) => (
              <MenuItem value={option}>{option}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <ButtonGroup variant="contained">
          <Button type="reset" variant="contained">
            Default
          </Button>
          <Button type="submit" variant="contained">
            Generate
          </Button>
        </ButtonGroup>
      </Stack>
    );
  } else {
    return (
      <Typography variant="p1">
        At least one model must be present to perform inference. Right click the
        graph area and select "import model" to add one.
      </Typography>
    );
  }
}

export default Variation;
