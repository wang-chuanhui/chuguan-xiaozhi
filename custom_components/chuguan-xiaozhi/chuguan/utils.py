import asyncio
import psutil
import logging
from .model import SockResponse
import subprocess

from typing import List, Optional

_LOGGER = logging.getLogger(__name__)


def get_all_macs():
    """返回所有非回环网卡的 MAC 地址字典"""
    macs = {}
    for name, addrs in psutil.net_if_addrs().items():
        # 跳过回环接口
        if name == 'lo':
            continue
        for addr in addrs:
            if addr.family == psutil.AF_LINK:  # AF_LINK 表示 MAC
                macs[name] = addr.address.lower()
    return macs
def get_main_mac():
    """返回主网卡的 MAC 地址"""
    macs = get_all_macs()
    # 通常主网卡是 eth0 或 wlan0
    for name in ['wlan0', 'eth0', 'en0']:
        if name in macs:
            return macs[name]
    # 如果以上都没有，返回第一个找到的 MAC
    return next(iter(macs.values())) if macs else None


async def send_messages(message: str):
    """Upload entities"""
    writer = None
    try:
        reader, writer = await asyncio.open_unix_connection("/tmp/frpc_loader.sock")
        writer.write(message.encode())
        await writer.drain()   # 确保发送出去
        writer.write_eof()     # 相当于 shutdown(SHUT_WR)
        response = await reader.read(1024 * 1024)
        res = response.decode()
        _LOGGER.info(res)
        obj = SockResponse.model_validate_json(res)
        return obj
    except Exception as e:
        _LOGGER.error(f"write to /tmp/frpc_loader.sock error: {e}")
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()


def execute_shell(args: list[str]):
    try:
        res = subprocess.run(
            args, 
            capture_output=True, 
            text=True, 
            cwd="/"
        )
        content = res.stdout.strip()
        return content
    except Exception as e:
        _LOGGER.error(f"execute shell error: {e}")
        return None


async def async_execute_shell(args: List[str]) -> Optional[str]:
    """
    异步执行 shell 命令
    """
    try:
        # 1. 创建子进程
        # 注意：这里使用传入的 args 列表，不需要 shell=True
        _LOGGER.info(f"async_execute_shell with args {args}")
        proc = await asyncio.create_subprocess_exec(
            *args,  # 解包参数列表
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/"  # 设置工作目录
        )

        # 2. 等待命令执行完成，并获取输出
        # communicate() 会自动处理死锁问题，并返回 (stdout, stderr)
        stdout, stderr = await proc.communicate()

        # 3. 解码并返回结果
        # 如果命令执行失败（返回非0），可以根据需要记录日志，但不要抛出异常中断逻辑
        if proc.returncode != 0:
            _LOGGER.warning(f"Shell command exited with code {proc.returncode}: {stderr.decode().strip()}")

        content = stdout.decode().strip()
        return content

    except Exception as e:
        _LOGGER.error(f"Execute shell error: {e}")
        return None