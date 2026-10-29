"""Local Hugging Face transformers backend (protocol v4 §5): pinned revision, explicit greedy decoding, batch size 1."""
import hashlib
import platform
import time

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig

DTYPES = {"float32": torch.float32, "float16": torch.float16, "bfloat16": torch.bfloat16}


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def pick_device():
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class HFLocal:
    def __init__(self, model_key, model_cfg, gen_cfg, device=None, dtype="float32"):
        self.model_key = model_key
        self.model_id = model_cfg["hf_id"]
        self.revision = model_cfg["revision"]
        self.device = device or pick_device()
        self.dtype_name = dtype
        torch.manual_seed(gen_cfg["seed"])
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id, revision=self.revision, dtype=DTYPES[dtype]
        ).to(self.device)
        self.model.eval()
        repo_gc = self.model.generation_config
        # Built from scratch so sampling knobs and penalties in the repo's generation_config.json are not inherited.
        self.gen_config = GenerationConfig(
            do_sample=gen_cfg["do_sample"],
            num_beams=gen_cfg["num_beams"],
            max_new_tokens=gen_cfg["max_new_tokens"],
            repetition_penalty=gen_cfg["repetition_penalty"],
            eos_token_id=repo_gc.eos_token_id,
            pad_token_id=repo_gc.pad_token_id if repo_gc.pad_token_id is not None else self.tokenizer.eos_token_id,
            bos_token_id=repo_gc.bos_token_id,
        )
        self.repo_generation_config = repo_gc.to_diff_dict()
        # transformers 4.57 re-applies model-specific defaults (e.g. Qwen's do_sample=True, temperature=0.7)
        # to any passed-in field that equals the global default, so the model's own config must be replaced too.
        self.model.generation_config = self.gen_config
        eos = repo_gc.eos_token_id
        self.eos_ids = set(eos if isinstance(eos, list) else [eos])

    def env(self):
        gpu = torch.cuda.get_device_name(0) if self.device == "cuda" else (platform.processor() or platform.machine())
        info = {
            "device": self.device,
            "gpu_name": gpu,
            "dtype": self.dtype_name,
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "cuda_version": torch.version.cuda,
            "platform": platform.platform(),
        }
        info["env_hash"] = sha256(repr(sorted(info.items())))[:16]
        return info

    def render(self, system_text, user_text):
        messages = [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}]
        return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    @torch.inference_mode()
    def generate(self, system_text, user_text):
        rendered = self.render(system_text, user_text)
        enc = self.tokenizer(rendered, return_tensors="pt", add_special_tokens=False).to(self.device)
        t0 = time.perf_counter()
        out = self.model.generate(**enc, generation_config=self.gen_config)
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        new_ids = out[0, enc["input_ids"].shape[1]:].tolist()
        hit_eos = bool(new_ids) and new_ids[-1] in self.eos_ids
        text = self.tokenizer.decode(new_ids, skip_special_tokens=True).strip()
        return {
            "text": text,
            "model_id": self.model_id,
            "model_revision": self.revision,
            "rendered_prompt": rendered,
            "rendered_prompt_sha256": sha256(rendered),
            "input_tokens": int(enc["input_ids"].shape[1]),
            "output_tokens": len(new_ids),
            "finish_reason": "eos" if hit_eos else ("length" if len(new_ids) >= self.gen_config.max_new_tokens else "other"),
            "latency_ms": latency_ms,
            "generation_config": self.gen_config.to_diff_dict(),
            "raw_response": self.tokenizer.decode(new_ids, skip_special_tokens=False),
        }
