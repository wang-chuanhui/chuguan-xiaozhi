import asyncio
import re
import os
import logging


_LOGGER = logging.getLogger(__name__)

async def get_audio_status():
    # 设置自定义环境变量（对应 Node.js 中的 customEnv）
    custom_env = os.environ.copy()
    custom_env.update({
        'LANG': 'en_US.UTF-8',
        'LC_ALL': 'en_US.UTF-8',
        'LC_MESSAGES': 'en_US.UTF-8',
        'LANGUAGE': 'en_US.UTF-8'
    })
    # custom_env['YOUR_CUSTOM_VAR'] = 'value'  # 如果有具体的环境变量，在这里添加

    try:
        # 创建两个异步子进程任务，对应 Promise.all 的并发执行
        vol_task = asyncio.create_subprocess_shell(
            "pactl get-sink-volume @DEFAULT_SINK@",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=custom_env
        )
        mute_task = asyncio.create_subprocess_shell(
            "pactl get-sink-mute @DEFAULT_SINK@",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=custom_env
        )

        # 启动进程并等待两个命令同时执行完毕（相当于 Promise.all）
        vol_proc, mute_proc = await asyncio.gather(vol_task, mute_task)
        
        # 获取标准输出（默认是字节，需要解码为字符串）
        vol_stdout, _ = await vol_proc.communicate()
        mute_stdout, _ = await mute_proc.communicate()
        
        vol_res = vol_stdout.decode('utf-8')
        mute_res = mute_stdout.decode('utf-8')

        # 解析音量：匹配第一个出现的百分比数字
        vol_match = re.search(r'(\d+)%', vol_res)
        volume = int(vol_match.group(1)) if vol_match else 0

        # 解析静音状态：匹配 Mute: yes 或 Mute: no
        muted = 'yes' in mute_res.lower()

        return {"volume": volume, "muted": muted}

    except Exception as e:
        raise Exception(f"无法获取音量信息: {e}")

async def get_volume():
    result = await get_audio_status()
    if result["muted"]:
        return 0
    else:
        return result["volume"]

async def set_volume(value: int):
    # 校验音量值是否在 0-100 之间
    if not (0 <= value <= 100):
        raise ValueError('音量必须在 0-100 之间')

    try:
        # 准备环境变量，确保 pactl 输出英文，避免解析异常
        custom_env = os.environ.copy()
        custom_env.update({
            'LANG': 'en_US.UTF-8',
            'LC_ALL': 'en_US.UTF-8',
            'LC_MESSAGES': 'en_US.UTF-8',
            'LANGUAGE': 'en_US.UTF-8'
        })

        # 异步执行 pactl 命令设置音量
        process = await asyncio.create_subprocess_shell(
            f"pactl set-sink-volume @DEFAULT_SINK@ {value}%",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=custom_env
        )
        
        # 等待子进程执行完毕
        await process.wait()

    except Exception as e:
        raise Exception(f"设置音量失败: {e}")

async def get_mute():
    result = await get_audio_status()
    return result["muted"]

async def set_mute(should_mute: bool):
    try:
        # 准备环境变量，确保 pactl 命令稳定执行
        custom_env = os.environ.copy()
        custom_env.update({
            'LANG': 'en_US.UTF-8',
            'LC_ALL': 'en_US.UTF-8',
            'LC_MESSAGES': 'en_US.UTF-8',
            'LANGUAGE': 'en_US.UTF-8'
        })

        # 将布尔值转换为 pactl 能识别的 1 (静音) 或 0 (取消静音)
        state = '1' if should_mute else '0'
        
        # 异步执行 pactl 命令设置静音状态
        process = await asyncio.create_subprocess_shell(
            f"pactl set-sink-mute @DEFAULT_SINK@ {state}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=custom_env
        )
        
        # 等待子进程执行完毕
        await process.wait()

    except Exception as e:
        raise Exception(f"设置静音状态失败: {e}")


async def watch_volume(callback):
    # 准备环境变量
    custom_env = os.environ.copy()
    custom_env.update({
        'LANG': 'en_US.UTF-8',
        'LC_ALL': 'en_US.UTF-8',
        'LC_MESSAGES': 'en_US.UTF-8',
        'LANGUAGE': 'en_US.UTF-8'
    })

    try:
        # 启动 pactl subscribe 订阅进程
        # 注意：这里使用 create_subprocess_exec 直接传入命令和参数，比 shell 更安全
        monitor = await asyncio.create_subprocess_exec(
            'pactl', 'subscribe',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=custom_env
        )

        # 异步逐行读取 pactl 订阅进程的输出
        async def read_stdout():
            if monitor.stdout is None:
                return
            async for line in monitor.stdout:
                output = line.decode('utf-8').strip()
                
                # 过滤事件：只关心 sink (输出设备) 的 change 事件
                if "Event 'change' on sink" in output:
                    # 触发变化时，重新获取当前音量状态并执行回调
                    try:
                        info = await get_audio_status()
                        # 如果回调是普通函数，直接调用；如果是异步函数，用 await
                        if asyncio.iscoroutinefunction(callback):
                            await callback(info)
                        else:
                            callback(info)
                    except Exception as err:
                        _LOGGER.error(f'获取音量失败: {err}')

        # 启动读取任务（相当于 Node.js 中的 stdout.on('data') 监听）
        read_task = asyncio.create_task(read_stdout())
        
        # 返回进程实例，方便外部后续调用 monitor.terminate() 来手动停止监控
        return monitor

    except Exception as err:
        _LOGGER.error(f'监控进程启动错误: {err}')
        return None

