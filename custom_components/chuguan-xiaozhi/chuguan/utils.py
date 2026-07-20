import asyncio
import psutil
import logging
from .model import SockResponse
import subprocess
import aiohttp
import async_timeout
import aiofiles
import tempfile
import os


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

def is_gnome_running():
    try:
        # 执行 ps -e | grep gnome-session 命令
        # shell=True 允许使用管道符 |
        result = subprocess.run(
            "pgrep -f /usr/libexec/gnome-session-binary", 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        # 如果命令执行成功且有输出，说明找到了进程
        if result.returncode == 0 and result.stdout.strip():
            return True
        return False
        
    except Exception as e:
        _LOGGER.error(f"执行出错: {e}")
        return False


async def async_execute_shell(args: List[str]) -> Optional[str]:
    """
    异步执行 shell 命令
    """
    try:
        # 1. 创建子进程
        # 注意：这里使用传入的 args 列表，不需要 shell=True
        # _LOGGER.info(f"async_execute_shell with args {args}")
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
        # if proc.returncode != 0:
            # _LOGGER.warning(f"Shell command exited with code {proc.returncode}: {stderr.decode().strip()}")

        content = stdout.decode().strip()
        return content

    except Exception as e:
        _LOGGER.error(f"Execute shell error: {e}")
        return None
    


async def fetch_data(url: str, headers=None):
    """异步调用外部接口获取数据"""
    for attempt in range(3):
        try:
            async with async_timeout.timeout(30):  # 设置超时时间
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            _LOGGER.error(f"API request failed with status {response.status}")
                            return None
        except Exception as e:
            _LOGGER.error(f"Error fetching data: {e}")
            await asyncio.sleep(2 ** attempt)
            continue
    return None




async def download_file_to_tmp(url: str, filename: str) -> str:
    """异步流式下载文件到临时目录"""
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, filename)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"下载失败，状态码: {response.status}")
            
            # 异步分块写入文件，避免内存溢出
            async with aiofiles.open(file_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    await f.write(chunk)
                    
    return file_path


def get_monitor_status():
    try:
        # 执行 xset q 命令
        result = subprocess.run(
            ['xset', 'q'], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True, 
            env={'DISPLAY': ':0'}
        )
        
        # 逐行读取输出，找到包含 "Monitor" 的那一行
        for line in result.stdout.splitlines():
            if 'Monitor' in line:
                # 假设输出格式是 "Monitor is On" 或 "Monitor is Off"
                # 取这一行最后一个单词就是状态
                status = line.strip().split()[-1].lower()
                return status == 'on'
                
        return False
        
    except Exception as e:
        # _LOGGER.error(f"执行出错: {e}")
        return False

def set_monitor_status(on: bool):
    try:
        # 执行 xset q 命令
        result = subprocess.run(
            ['xset', 'dpms', 'force', 'on' if on else 'off'], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True, 
            env={'DISPLAY': ':0'}
        )
        
        return result.stdout.strip()
        
    except Exception as e:
        _LOGGER.error(f"执行出错: {e}")
        return False