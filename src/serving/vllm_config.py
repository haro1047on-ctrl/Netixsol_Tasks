"""
src/serving/vllm_config.py
==========================
Zarya Digital Bank (Pakistan) — vLLM Production Serving Configuration

Configures high-throughput vLLM OpenAI-compatible inference server with:
- PagedAttention (virtual memory paging for non-contiguous KV caches)
- Iteration-Level Continuous Batching (Orca/vLLM style dynamic request scheduling)
- 4-bit AWQ Tensor Core acceleration
- Chunked Prefill (max 512 tokens per prefill chunk to eliminate latency spikes)
"""

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class VLLMServerConfig:
    """Production configuration parameters for vLLM server."""
    model_path: str = os.getenv("VLLM_MODEL_PATH", "models/zarya-qwen2.5-3b-awq")
    served_model_name: str = os.getenv("VLLM_SERVED_NAME", "zarya-qwen2.5-3b-awq")
    quantization: Optional[str] = "awq"  # "awq", "bitsandbytes", or None
    max_model_len: int = 2048
    gpu_memory_utilization: float = 0.90
    block_size: int = 16  # PagedAttention cache block size
    tensor_parallel_size: int = 1
    max_num_batched_tokens: int = 4096
    max_num_seqs: int = 256
    enable_chunked_prefill: bool = True
    port: int = int(os.getenv("VLLM_PORT", "8000"))
    host: str = os.getenv("VLLM_HOST", "0.0.0.0")

    def build_cli_command(self) -> List[str]:
        """Constructs the exact bash/cmd line to launch vLLM."""
        cmd = [
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", self.model_path,
            "--served-model-name", self.served_model_name,
            "--host", self.host,
            "--port", str(self.port),
            "--max-model-len", str(self.max_model_len),
            "--gpu-memory-utilization", str(self.gpu_memory_utilization),
            "--tensor-parallel-size", str(self.tensor_parallel_size),
            "--max-num-seqs", str(self.max_num_seqs),
            "--block-size", str(self.block_size),
            "--trust-remote-code",
        ]
        if self.quantization:
            cmd.extend(["--quantization", self.quantization])
        if self.enable_chunked_prefill:
            cmd.append("--enable-chunked-prefill")
        return cmd


def get_default_vllm_config() -> VLLMServerConfig:
    return VLLMServerConfig()


if __name__ == "__main__":
    cfg = get_default_vllm_config()
    print("🚀 Default vLLM Startup Command:")
    print(" ".join(cfg.build_cli_command()))
