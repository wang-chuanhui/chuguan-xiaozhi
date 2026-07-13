from enum import StrEnum
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.components.number import NumberEntity, NumberDeviceClass, NumberMode
from .chuguan.RealDevice import realDevice
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
import logging
import datetime
from homeassistant.components.update import UpdateEntity, UpdateDeviceClass, UpdateEntityFeature, _version_is_newer
from .chuguan.hub import getAlreadyExistHub
from .chuguan.utils import download_file_to_tmp
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)


class KeyType(StrEnum):
    MOTION = 'motion'
    PRESENCE = 'presence'
    MOTION_DISTANCE_MIN = 'motion_distance_min'
    PRESENCE_DISTANCE_MIN = 'presence_distance_min'
    MOTION_DISTANCE_MAX = 'motion_distance_max'
    PRESENCE_DISTANCE_MAX = 'presence_distance_max'
    MOTION_SENSITIVITY = 'motion_sensitivity'
    PRESENCE_SENSITIVITY = 'presence_sensitivity'
    MOTION_CYCLE = 'motion_cycle'
    PRESENCE_CYCLE = 'presence_cycle'


class MotionBinarySensor(BinarySensorEntity):
    """A binary sensor entity."""
    def __init__(self):
        """Initialize the motion binary sensor."""
        super().__init__()
        self._attr_unique_id = f"human_motion"
        self._attr_name = f"运动感应"
        self._attr_device_class = BinarySensorDeviceClass.MOTION
        self._is_on = False
        self._attr_device_info = realDevice.motionDevice

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._is_on
    
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._is_on = await realDevice.getKV("motion_on") == '1'
        self.schedule_update_ha_state()
        # self.async_on_remove(
        #     async_track_time_interval(self.hass, self.update_is_on, timedelta(seconds=1))
        # )
        self.async_on_remove(
            self.hass.bus.async_listen('chuguan_xiaozhi_real_device_update_value', self.update_is_on)
        )
    
    async def update_is_on(self, now):
        """Update the binary sensor state."""
        oldValue = self._is_on
        self._is_on = await realDevice.getKV('motion_on') == '1'
        if oldValue == self._is_on:
            return
        self.schedule_update_ha_state()

class PresenceBinarySensor(BinarySensorEntity):
    """"""

    def __init__(self):
        super().__init__()
        self._attr_unique_id = "human_presence"
        self._attr_name = f"人体存在"
        self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY
        self._is_on = False
        self._attr_device_info = realDevice.presenceDevice

    @property
    def is_on(self) -> bool:
        return self._is_on
    
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._is_on = await realDevice.getKV("presence_on") == '1'
        self.schedule_update_ha_state()
        # self.async_on_remove(
        #     async_track_time_interval(self.hass, self.update_is_on, timedelta(seconds=1))
        # )
        self.async_on_remove(
            self.hass.bus.async_listen('chuguan_xiaozhi_real_device_update_value', self.update_is_on)
        )
    
    async def update_is_on(self, now):
        oldValue = self._is_on
        self._is_on = await realDevice.getKV('presence_on') == '1'
        if oldValue == self._is_on:
            return
        self.schedule_update_ha_state()

class DistanceSensor(SensorEntity):
    """距离传感器（支持运动和存在距离）"""
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = "cm"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, name: str, distance_type: KeyType):
        self._distance_type = distance_type  # 'motion' 或 'presence'
        self._attr_name = name
        self._attr_unique_id = f"human_{distance_type}_distance"
        if distance_type == KeyType.MOTION:
            self._attr_device_info = realDevice.motionDevice
        elif distance_type == KeyType.PRESENCE:
            self._attr_device_info = realDevice.presenceDevice
        self._distance = 0

    @property
    def native_value(self):
        return self._distance
    
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        await self.update_Distance(None)
        # self.async_on_remove(
        #     async_track_time_interval(self.hass, self.update_Distance, timedelta(seconds=1))
        # )
        self.async_on_remove(
            self.hass.bus.async_listen('chuguan_xiaozhi_real_device_update_value', self.update_Distance)
        )
    
    async def update_Distance(self, now):
        newValue = 0
        if self._distance_type == KeyType.MOTION:
            newValue = await realDevice.getKV('motion_distance')
        elif self._distance_type == KeyType.PRESENCE:
            newValue = await realDevice.getKV('presence_distance')
        if newValue == '':
            return
        if newValue == self._distance:
            return
        self._distance = newValue
        self.schedule_update_ha_state()
    

class SettingNumber(NumberEntity):
    """"""
    def __init__(self, name: str, key: KeyType):
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{key}_setting"
        self._attr_entity_category = EntityCategory.CONFIG

        if "motion" in key:
            self._attr_device_info = realDevice.motionDevice
        elif "presence" in key:
            self._attr_device_info = realDevice.presenceDevice

        # 根据类型设置不同的范围和步进
        if "cycle" in key:  # 存在判断周期
            self._attr_native_min_value = 1
            self._attr_native_max_value = 60
            self._attr_native_step = 1
            self._native_value = 2
            self._attr_native_unit_of_measurement = "min"
            self._attr_device_class = NumberDeviceClass.DURATION
            self._attr_mode = NumberMode.SLIDER
        elif "sensitivity" in key:  # 灵敏度
            self._attr_native_min_value = 0
            self._attr_native_max_value = 12
            self._attr_native_step = 1
            self._native_value = 12 - 4
            self._attr_mode = NumberMode.SLIDER
        elif "distance" in key:  # 距离阈值 (最小/最大值)
            self._attr_native_min_value = 100
            self._attr_native_max_value = 500
            self._attr_native_step = 1
            if 'min' in key:
                self._native_value = 100
            elif 'max' in key:
                self._native_value = 300
            self._attr_native_unit_of_measurement = "cm"
            self._attr_device_class = NumberDeviceClass.DISTANCE
            self._attr_mode = NumberMode.SLIDER
        self._native_value = 0


    @property
    def native_value(self):
        return self._native_value
    
    async def async_set_native_value(self, value: float):
        """当用户在 HA 界面拖动滑块或输入数值时触发"""
        # 将新参数写入底层硬件/雷达模块
        if "min" in self._key:
            maxKey = self._key.replace('min', 'max')
            maxValue = await realDevice.getKV(maxKey)
            if maxValue != '' and maxValue != None:
                if value > float(maxValue):
                    value = float(maxValue)
                    if value == self._native_value:
                        value = value - 1
        elif "max" in self._key:
            minKey = self._key.replace('max', 'min')
            minValue = await realDevice.getKV(minKey)
            if minValue != '' and minValue != None:
                if value < float(minValue):
                    value = float(minValue)
                    if value == self._native_value:
                        value = value + 1
        await realDevice.setKV(self._key, str(int(value)))
        await self.update_value()

    async def update_value(self, now=None):
        value = await realDevice.getKV(self._key)
        if value == '' or value == None:
            return
        if value == self._native_value:
            return
        self._native_value = float(value)
        if self.hass:
            self.schedule_update_ha_state()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        await self.update_value(None)
        # self.async_on_remove(
        #     async_track_time_interval(self.hass, self.update_value, timedelta(seconds=1))
        # )

class EnvironmentStudyButton(ButtonEntity):
    """环境学习按钮"""

    def __init__(self, on: bool):
        self._on = on
        if on:
            self._attr_name = "执行环境学习"
        else:
            self._attr_name = "停止环境学习"
        self._attr_unique_id = f"environment_study_button_{self._on}"
        self._attr_device_info = realDevice.device

    async def async_press(self):
        if self._on:
            await realDevice.begin_learn()
        else:
            await realDevice.end_learn()

class EnvironmentStudySensor(BinarySensorEntity):
    """环境学习传感器"""
    def __init__(self):
        self._attr_name = "环境学习"
        self._attr_unique_id = "environment_study_status"
        self._attr_device_info = realDevice.device
        self._is_on = False
        self._attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self):
        return self._is_on
    
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._is_on = await realDevice.getKV('environment_study') == '1'
        self.schedule_update_ha_state()
        # self.async_on_remove(
        #     async_track_time_interval(self.hass, self.update_value, timedelta(seconds=1))
        # )
        self.async_on_remove(
            self.hass.bus.async_listen('chuguan_xiaozhi_real_device_update_value', self.update_value)
        )

    async def update_value(self, now=None):
        self._is_on = await realDevice.getKV('environment_study') == '1'
        if self.hass:
            self.schedule_update_ha_state()

class HardwareMonitorButton(ButtonEntity):
    """硬件监控按钮"""

    def __init__(self):
        self._attr_name = "执行扩展板监控"
        self._attr_unique_id = "hardware_monitor_button"
        self._attr_device_info = realDevice.device
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_press(self):
        await realDevice.start(self.hass)

class HardwareMonitorSensor(BinarySensorEntity):
    """硬件监控传感器"""
    def __init__(self):
        self._attr_name = "扩展板监控"
        self._attr_unique_id = "hardware_monitor_status"
        self._attr_device_info = realDevice.device
        self._is_on = False
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        return self._is_on
    
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._is_on = realDevice.is_monitor
        self.schedule_update_ha_state()
        # self.async_on_remove(
        #     async_track_time_interval(self.hass, self.update_value, timedelta(seconds=1))
        # )
        self.async_on_remove(
            self.hass.bus.async_listen('chuguan_xiaozhi_real_device_update_value', self.update_value)
        )

    async def update_value(self, now=None):
        self._is_on = realDevice.is_monitor
        if self.hass:
            self.schedule_update_ha_state()

class CheckUpdateButton(ButtonEntity):
    """检查更新按钮"""

    def __init__(self):
        self._attr_name = "检查更新"
        self._attr_unique_id = "check_update_button"
        self._attr_device_info = realDevice.device
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_press(self):
        self.hass.bus.async_fire('chuguan_xiaozhi_real_device_check_update')

        

class FirmwareUpdateEntity(UpdateEntity):

    def __init__(self):
        self._attr_name = "扩展板固件更新"
        self._attr_unique_id = "firmware_update"
        self._attr_device_info = realDevice.device
        self._attr_device_class = UpdateDeviceClass.FIRMWARE
        self._attr_supported_features = UpdateEntityFeature.INSTALL
        

    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture to use in the frontend.

        Update entities return the brand icon based on the integration
        domain by default.
        """
        # return (
        #     f"https://brands.home-assistant.io/_/chuguan_home/icon.png"
        # )
        return None
    
    async def check_update(self, now=None):
        hub = getAlreadyExistHub()
        if hub is None:
            return
        install_version = await hub.store.async_get_key_value('install_version')
        if install_version is None:
            install_version = ''
        self._attr_installed_version = install_version
        self._attr_latest_version = install_version
        data = await realDevice.get_firmware_update()
        if data:
            self._attr_latest_version = data.get('version', install_version)
            self._attr_release_summary = data.get('summary', '')
            self._attr_release_url = data.get('url', '')
            self._download = data.get('download', '')
            self._name = data.get('name', '')
        self.schedule_update_ha_state()

    
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        await self.check_update()
        self.async_on_remove(
            self.hass.bus.async_listen('chuguan_xiaozhi_real_device_check_update', self.check_update)
        )

    async def async_install(self, version: str | None, backup: bool, **kwargs):
        _LOGGER.info(f"install firmware, version: {version}, backup: {backup}, kwargs: {kwargs}")
        if self._download == '':
            raise Exception("download url is empty")
        name = f"{self._name}_{self._attr_latest_version}.hex"
        filepath = await download_file_to_tmp(self._download, name)
        _LOGGER.info(f"download firmware to {filepath}")
        success = await realDevice.install_firmware(filepath)
        _LOGGER.info(f"install firmware success: {success}")
        if success:
            hub = getAlreadyExistHub()
            if hub:
                await hub.store.async_set_key_value('install_version', self._attr_latest_version)
            await self.check_update()


    def release_notes(self) -> str | None:
        """Return full release notes.

        This is suitable for a long changelog that does not fit in the release_summary
        property. The returned string can contain markdown.
        """
        raise "NotImplementedError"
    
def getAllBinarySensor():
    return [MotionBinarySensor(), PresenceBinarySensor(), EnvironmentStudySensor(), HardwareMonitorSensor()]

def getAllSensor():
    return [DistanceSensor("人体存在目标距离", 'presence'), DistanceSensor("运动感应目标距离", 'motion')]

def getAllNumber():
    return [
        SettingNumber("判断周期", KeyType.PRESENCE_CYCLE),
        SettingNumber("灵敏度", KeyType.MOTION_SENSITIVITY),
        SettingNumber("灵敏度", KeyType.PRESENCE_SENSITIVITY),
        SettingNumber("最小距离", KeyType.MOTION_DISTANCE_MIN),
        SettingNumber("最小距离", KeyType.PRESENCE_DISTANCE_MIN),
        SettingNumber("最大距离", KeyType.MOTION_DISTANCE_MAX),
        SettingNumber("最大距离", KeyType.PRESENCE_DISTANCE_MAX),
    ]

def getAllButton():
    return [EnvironmentStudyButton(True), CheckUpdateButton(), HardwareMonitorButton()]

def getAllUpdate():
    return [FirmwareUpdateEntity()]