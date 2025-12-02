import asyncio
import os
import tempfile


async def execute_code(
    code: str, timeout: float, memory_limit: int | None = None
) -> tuple[bool, str]:
    file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ts", encoding="utf-8", delete=False
        ) as tmp_f:
            file_path = tmp_f.name
            tmp_f.write(code)
            tmp_f.flush()

            cmd = ["ts-node", "--compiler-options", '{"module": "commonjs"}', file_path]

            env = os.environ.copy()
            if memory_limit:
                # memory_limit is in MB
                env["NODE_OPTIONS"] = f"--max-old-space-size={memory_limit}"

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                stdout_str = stdout.decode().strip()
                stderr_str = stderr.decode().strip()

                if proc.returncode == 0:
                    return True, stdout_str
                else:
                    return False, f"failed [exit {proc.returncode}]: {stderr_str}"
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return False, "failed: timeout"
    except Exception as e:
        return False, f"failed: [{type(e).__name__}] {e}"
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
