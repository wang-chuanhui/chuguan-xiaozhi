import os
import subprocess
import logging

_LOGGER = logging.getLogger(__name__)

# 使用 os.path.join 拼接路径，与 Node.js 的 path.join 对应
bin_path = os.path.join('/usr/local/bin', 'lcd_brightness')

def get_brightness():
    try:
        # 执行 sudo 命令获取亮度，cwd="/" 对应 Node.js 中的 {cwd: "/"}
        res = subprocess.run(
            ['sudo', bin_path, '-g'], 
            capture_output=True, 
            text=True, 
            cwd="/"
        )
        content = res.stdout.strip()
        _LOGGER.debug(content)
        
        # 解析输出：匹配 "Current backlight: XX%"
        if content.startswith('Current backlight: '):
            # 去掉前缀和后缀的百分号，提取数值
            value = content.replace('Current backlight: ', '').replace('%', '')
            return int(value)
    except Exception as e:
        _LOGGER.error(f"获取亮度失败: {e}")
        
    return 100

def no_sudo_get_brightness():
    try:
        # 执行 sudo 命令获取亮度，cwd="/" 对应 Node.js 中的 {cwd: "/"}
        res = subprocess.run(
            ['cat', '/lcd_brightness.conf'], 
            capture_output=True, 
            text=True, 
            cwd="/"
        )
        content = res.stdout.strip()
        _LOGGER.debug(content)
        return int(content)
    except Exception as e:
        _LOGGER.error(f"获取亮度失败: {e}")
        
    return 100

def set_brightness(value: int):
    try:
        # 执行 sudo 命令设置亮度，处理 value 为 0 或 None 的情况
        res = subprocess.run(
            ['sudo', bin_path, str(value or 1)], 
            capture_output=True, 
            text=True, 
            cwd="/"
        )
        content = res.stdout.strip()
        _LOGGER.debug(content)
        
        # 解析输出：匹配 "Set backlight to XX%, ..."
        if content.startswith('Set backlight to '):
            # 先按逗号分割，取第一部分，再去掉前缀和百分号
            item = content.split(',')[0]
            set_value = item.replace('Set backlight to ', '').replace('%', '')
            return int(set_value)
    except Exception as e:
        _LOGGER.error(f"设置亮度失败: {e}")
        
    return value


def is_screen_on():
    """判断屏幕是否打开"""
    # gdbus call --session --dest org.gnome.Mutter.DisplayConfig --object-path /org/gnome/Mutter/DisplayConfig --method org.freedesktop.DBus.Properties.Get org.gnome.Mutter.DisplayConfig PowerSaveMode
    try:
        # 执行 sudo 命令获取亮度，cwd="/" 对应 Node.js 中的 {cwd: "/"}
        res = subprocess.run(
            ['gdbus', 'call', '--session', '--dest', 'org.gnome.Mutter.DisplayConfig', '--object-path', '/org/gnome/Mutter/DisplayConfig', '--method', 'org.freedesktop.DBus.Properties.Get', 'org.gnome.Mutter.DisplayConfig', 'PowerSaveMode'], 
            capture_output=True, 
            text=True, 
            cwd="/"
        )
        content = res.stdout.strip()
        # (<0>,)
        content = content.replace('(<', '').replace('>,)', '')
        return int(content) == 0
    except Exception as e:
        _LOGGER.error(f"获取屏幕状态失败: {e}")
    return True
