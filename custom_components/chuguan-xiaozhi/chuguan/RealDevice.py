from .utils import async_execute_shell, fetch_data
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
import logging
import asyncio
from homeassistant.core import HomeAssistant
from .store import MyStore
import re
import json


_LOGGER = logging.getLogger(__name__)

via_device=(DOMAIN, "ha_screen_device")

class RealDevice:

    device = DeviceInfo(manufacturer="初冠", model="小智", name="HA屏", identifiers={via_device}, model_id="cgxz")
    
    way1Device = DeviceInfo(manufacturer="初冠", model="小智", name="按键1", identifiers={(DOMAIN, "device_way_1")}, model_id="cgxz", via_device=via_device)
    way2Device = DeviceInfo(manufacturer="初冠", model="小智", name="按键2", identifiers={(DOMAIN, "device_way_2")}, model_id="cgxz", via_device=via_device)
    way3Device = DeviceInfo(manufacturer="初冠", model="小智", name="按键3", identifiers={(DOMAIN, "device_way_3")}, model_id="cgxz", via_device=via_device)
    presenceDevice = DeviceInfo(manufacturer="初冠", model="小智", name="人体存在", identifiers={(DOMAIN, "device_human_presence")}, model_id="cgxz", via_device=via_device)
    motionDevice = DeviceInfo(manufacturer="初冠", model="小智", name="运动感应", identifiers={(DOMAIN, "device_human_motion")}, model_id="cgxz", via_device=via_device)

    motion_on = False
    motion_distance: int | None = None
    presence_on = False
    presence_distance: int | None = None
    way_1 = False
    way_2 = False
    way_3 = False

    is_monitor = False

    def __init__(self):
        """"""
        _LOGGER.info("RealDevice init")
        self._process: asyncio.subprocess.Process | None = None
        self._task: asyncio.Task | None = None
        self._learn_process: asyncio.subprocess.Process | None = None
        self._learn_task: asyncio.Task | None = None
        self.hass: HomeAssistant | None = None
        self.store: MyStore | None = None
        self.target_name: str | None = None


    async def start(self, hass: HomeAssistant):
        """启动雷达监控子进程"""
        try:
            await self.stop()
            self.target_name = await self.get_target_name()
            await self.resetKeySetting()
            await self.setLed()
            status = await async_execute_shell(["radar_key", "--status", "--query-relay"])
            await self.parse_line(status)
            self._process = await asyncio.create_subprocess_exec(
                "stdbuf", "-oL", "radar_key", "--poll", "0",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            # 将读取任务作为后台任务运行
            self.hass = hass
            self._task = self.hass.async_create_background_task(self._read_loop(), "radar_key_monitor")
            _LOGGER.info("Radar monitor started successfully.")
            self.is_monitor = True
        except FileNotFoundError:
            _LOGGER.error("radar_key command not found. Please check installation.")
            self.is_monitor = False
        except Exception as e:
            _LOGGER.error(f"Error starting radar monitor: {e}")
            self.is_monitor = False
        await self.update_value('is_monitor', self.is_monitor)

    async def _read_loop(self):
        """持续读取并解析雷达输出"""
        assert self._process is not None and self._process.stdout is not None
        
        while not self._process.stdout.at_eof():
            try:
                raw_line = await self._process.stdout.readline()
                if not raw_line:
                    break
                    
                line = raw_line.decode('utf-8').strip()
                await self.parse_line(line)
            except asyncio.CancelledError:
                _LOGGER.info("Radar monitor task cancelled.")
                break
            except Exception as e:
                _LOGGER.error(f"Error reading radar output: {e}")
        self.is_monitor = False
        await self.update_value('is_monitor', self.is_monitor)


    async def parse_line(self, line: str):
        """解析雷达输出行"""
        # _LOGGER.warning(line)
        if not line:
            return
        if "运动触发:" in line:
            match = re.search(r'运动触发:\s*([是否])', line)
            motion_on = False
            if match:
                motion_on = match.group(1).strip() == '是'
            if motion_on != self.motion_on:
                self.motion_on = motion_on
                await self.update_value('motion_on', motion_on)
        if "存在触发:" in line:
            match = re.search(r'存在触发:\s*([是否])', line)
            presence_on = False
            if match:
                presence_on = match.group(1).strip() == '是'
            if presence_on != self.presence_on:
                self.presence_on = presence_on
                await self.update_value('presence_on', presence_on)
        if "运动目标距离:" in line:
            match = re.search(r'运动目标距离:\s*(\d+\s*cm|无)', line)
            value = '无'
            distance = None
            if match:
                value = match.group(1).strip()
            if value == '无':
                distance = None
            else:
                distance = int(value.replace('cm', ''))
            if distance != self.motion_distance:
                self.motion_distance = distance
                await self.update_value('motion_distance', distance)
        if "存在目标距离:" in line:
            match = re.search(r'存在目标距离:\s*(\d+\s*cm|无)', line)
            value = '无'
            distance = None
            if match:
                value = match.group(1).strip()
            if value == '无':
                distance = None
            else:
                distance = int(value.replace('cm', ''))
            if distance != self.presence_distance:
                self.presence_distance = distance
                await self.update_value('presence_distance', distance)
        if "继电器" in line:
            match = re.search(r'继电器\s*=\s*(.+)', line)
            if match:
                value = match.group(1).strip()
                items = value.split(' ')
                way_1 = items[0] == '1'
                way_2 = items[1] == '1'
                way_3 = items[2] == '1'
                if way_1 != self.way_1:
                    self.way_1 = way_1
                    await self.update_value('way_1', way_1)
                if way_2 != self.way_2:
                    self.way_2 = way_2
                    await self.update_value('way_2', way_2)
                if way_3 != self.way_3:
                    self.way_3 = way_3
                    await self.update_value('way_3', way_3)

    async def update_value(self, key: str, value: any):
        """更新指定键的值"""
        # _LOGGER.warning(f"update_value {key} {value}")
        self.hass.bus.async_fire(f"chuguan_xiaozhi_real_device_update_value", {key: value})

    async def stop(self):
        """安全停止雷达监控"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
                self._task = None
            except asyncio.CancelledError:
                _LOGGER.error("Radar monitor task cancelled error.")
            except Exception as e:
                _LOGGER.error(f"Error stopping radar monitor: {e}")
        
        if self._process:
            try:
                self._process.terminate()
                await self._process.wait()
                self._process = None
            except ProcessLookupError:
                _LOGGER.warning("Radar monitor process lookup not found.")
            except Exception as e:
                _LOGGER.error(f"Error stopping radar monitor: {e}")
        self.is_monitor = False
        await self.update_value('is_monitor', False)

    async def getWayOn(self, way: int) -> bool:
        if way == 1:
            return self.way_1
        elif way == 2:
            return self.way_2
        elif way == 3:
            return self.way_3
        return False
    
    async def setWayOn(self, way: int, value: bool):
        content = await async_execute_shell(['radar_key', '--relay', str(way - 1), '1' if value else '0'])
        await self.parse_line(content)

    async def getAllBrightness(self, on: bool) -> int:
        status = 'on' if on else 'off'
        if self.store:
            return await self.store.async_get_key_value(f'way_{status}_brightness') or 50
        return 50
    
    async def setLed(self):
        """设置LED状态, 2个亮度+3组RGB 长度20字节(关/开灯亮度0-100 + 3组灯开关灯色(先关灯色，后开灯色)"""
        args = ['radar_key', '--led']
        brightness_off = await self.getAllBrightness(False)
        brightness_on = await self.getAllBrightness(True)
        color_1_off = await self.getWayColor(1, False)
        color_1_on = await self.getWayColor(1, True)
        color_2_off = await self.getWayColor(2, False)
        color_2_on = await self.getWayColor(2, True)
        color_3_off = await self.getWayColor(3, False)
        color_3_on = await self.getWayColor(3, True)
        args.append(str(brightness_off))
        args.append(str(brightness_on))
        args.extend(map(str, color_1_off))
        args.extend(map(str, color_1_on))
        args.extend(map(str, color_2_off))  
        args.extend(map(str, color_2_on))
        args.extend(map(str, color_3_off))
        args.extend(map(str, color_3_on))
        _LOGGER.warning(f"设置LED状态: {' '.join(args)}")
        await async_execute_shell(args)
       
    async def setAllBrightness(self, on: bool, value: int):
        status = 'on' if on else 'off'
        if self.store:
            await self.store.async_set_key_value(f'way_{status}_brightness', value)
        await self.setLed()

    async def getWayColor(self, way: int, on: bool) -> tuple[int, int, int]:
        status = 'on' if on else 'off'
        if self.store:
            value = await self.store.async_get_key_value(f'way_{way}_{status}_color')
            if value and isinstance(value, list) and len(value) == 3:
                return value
        if on:
            return [255, 0, 0]
        return [0, 0, 255]
    
    async def setWayColor(self, way: int, on: bool, value: tuple[int, int, int]):
        status = 'on' if on else 'off'
        if self.store:
            await self.store.async_set_key_value(f'way_{way}_{status}_color', value)
        await self.setLed()
    
    async def getKV(self, key: str) -> str:
        if key == 'motion_on':
            return '1' if self.motion_on else '0'
        if key == 'presence_on':
            return '1' if self.presence_on else '0'
        if key == 'motion_distance':
            return self.motion_distance
        elif key == 'presence_distance':
            return self.presence_distance
        res = ''
        if self.store:
            res = await self.store.async_get_key_value(f'kv_{key}') or ''
        if res == '':
            if key == 'motion_distance_min':
                res = '100'
            elif key == 'motion_distance_max':
                res = '300'
            elif key == 'motion_sensitivity':
                res = '8'
            elif key == 'presence_distance_min':
                res = '100'
            elif key == 'presence_distance_max':
                res = '300'
            elif key == 'presence_sensitivity':
                res = '8'
            elif key == 'presence_cycle':
                res = '2'
        return res
    
    def modify_sensitivity(self,value: str | None) -> str:
        if value is None:
            return '8'
        return str(int(12 - float(value)))
    
    async def setKV(self, key: str, value: str):
        if self.store:
            await self.store.async_set_key_value(f'kv_{key}', value)
        radar_key = ''
        input_value = float(value)
        if key == 'motion_distance_min':
            radar_key = '--move-min'
        elif key == 'motion_distance_max':
            radar_key = '--move-max'
        elif key == 'motion_sensitivity':
            radar_key = '--move-sens'
            input_value = 12 - input_value
        elif key == 'presence_distance_min':
            radar_key = '--exist-min'
        elif key == 'presence_distance_max':
            radar_key = '--exist-max'
        elif key == 'presence_sensitivity':
            radar_key = '--exist-sens'
            input_value = 12 - input_value
        elif key == 'presence_cycle':
            radar_key = '--period'
            input_value = input_value * 60
        if radar_key:
            await async_execute_shell(['radar_key', radar_key, str(int(input_value))])

    async def resetKeySetting(self):
        value = await self.getKV('motion_distance_min')
        args = ['radar_key', '--move-min', value if value else '100']
        value = await self.getKV('motion_distance_max')
        args.extend(['--move-max', value if value else '300'])
        value = await self.getKV('motion_sensitivity')
        args.extend(['--move-sens', self.modify_sensitivity(value)])
        value = await self.getKV('presence_distance_min')
        args.extend(['--exist-min', value if value else '100'])
        value = await self.getKV('presence_distance_max')
        args.extend(['--exist-max', value if value else '300'])
        value = await self.getKV('presence_sensitivity')
        args.extend(['--exist-sens', self.modify_sensitivity(value)])
        value = await self.getKV('presence_cycle')
        input_value = float(value if value else '2') * 60
        args.extend(['--period', str(int(input_value))])
        _LOGGER.warning(f"重置键设置: {' '.join(args)}")
        await async_execute_shell(args)

    async def begin_learn(self):
        """开始环境学习"""
            # 1. 判断是否已经有进程和任务在执行
        if self._learn_process and self._learn_process.returncode is None:
            _LOGGER.warning("环境学习进程已在运行中，跳过本次启动。")
            return
            
        if self._learn_task and not self._learn_task.done():
            _LOGGER.warning("环境学习后台任务仍在运行中，跳过本次启动。")
            return
        try:
            self._learn_process = await asyncio.create_subprocess_exec(
                'radar_key', '--learn', 
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            self._learn_task = self.hass.async_create_background_task(self._learn_read_loop(), "radar_key_learn")
            _LOGGER.info("开始环境学习")
            await self.setKV('environment_study', '1')
            await self.update_value('environment_study', '1')
        except Exception as e:
            _LOGGER.error(f"开始环境学习失败: {e}")
        
    async def _learn_read_loop(self):
        """环境学习读取循环"""
        assert self._learn_process is not None and self._learn_process.stdout is not None

        while not self._learn_process.stdout.at_eof():
            try:
                raw_line = await self._learn_process.stdout.readline()
                if not raw_line:
                    break
                line = raw_line.decode().strip()
            except asyncio.CancelledError:
                _LOGGER.warning("环境学习任务已取消")
                break
            except Exception as e:
                _LOGGER.error(f"环境学习读取失败: {e}")
        _LOGGER.info("环境学习结束")
        await self.setKV('environment_study', '0')
        await self.update_value('environment_study', '0')

    async def end_learn(self):
        """结束环境学习"""
        if self._learn_task:
            self._learn_task.cancel()
            try:
                await self._learn_task
                self._learn_task = None
            except asyncio.CancelledError:
                pass
        if self._learn_process:
            try:
                self._learn_process.terminate()
                await self._learn_process.wait()
                self._learn_process = None
            except ProcessLookupError:
                pass
        _LOGGER.info("环境学习任务已取消")
        await self.setKV('environment_study', '0')
        await self.update_value('environment_study', '0')

    async def get_target_name(self):
        content = await async_execute_shell(['flasher', '--get-target-name'])
        if content is None:
            return None
        match = re.search(r'target_name: (\w+)', content)
        if match is None:
            return None
        name = match.group(1)
        _LOGGER.info(f"获取到的设备名称: {name}")
        return name

    async def get_firmware_update(self):
        """获取固件更新信息"""
        name = await self.get_target_name()
        if name is None:
            name = self.target_name
        if name is None:
            return None
        url = f'https://xcx.chuguankj.com/radar_firmware/{name}.json'
        data: dict | None = await fetch_data(url)
        if data is None:
            return None
        data['name'] = name
        _LOGGER.info(f"获取到的固件信息: {data}")
        return data
    
    async def install_firmware(self, filepath: str):
        """安装固件"""
        await self.stop()
        content = await async_execute_shell(['flasher', filepath])
        await asyncio.sleep(1)
        await self.start(self.hass)
        for i in range(5):
            if self.is_monitor != True:
                await asyncio.sleep(1)
                await self.start(self.hass)
            else:
                break
        if content:
            return "烧录成功" in content
        return False



realDevice = RealDevice()