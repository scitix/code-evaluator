import asyncio
import os
import tempfile


async def execute_code(code: str, timeout: float) -> tuple[bool, str]:
    file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", encoding="utf-8", delete=False
        ) as tmp_f:
            file_path = tmp_f.name
            tmp_f.write(code)
            tmp_f.flush()

            cmd = ["node", file_path]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
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
