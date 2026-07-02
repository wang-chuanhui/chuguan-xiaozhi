from enum import StrEnum
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.components.number import NumberEntity, NumberDeviceClass
from .chuguan.RealDevice import realDevice
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
from homeassistant.components.button import ButtonEntity

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
        self._is_on = await realDevice.getKV("motion_on")
        self.schedule_update_ha_state()
        self.async_on_remove(
            async_track_time_interval(self.hass, self.update_is_on, timedelta(seconds=1))
        )
    
    async def update_is_on(self, now):
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
        self._is_on = await realDevice.getKV("presence_on")
        self.schedule_update_ha_state()
        self.async_on_remove(
            async_track_time_interval(self.hass, self.update_is_on, timedelta(seconds=1))
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
    _attr_native_unit_of_measurement = "m"
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
        self.async_on_remove(
            async_track_time_interval(self.hass, self.update_Distance, timedelta(seconds=1))
        )
    
    async def update_Distance(self, now):
        newValue = 0
        if self._distance_type == KeyType.MOTION:
            newValue = await realDevice.getKV('motion_distance')
        elif self._distance_type == KeyType.PRESENCE:
            newValue = await realDevice.getKV('presence_distance')
        if newValue == '' or newValue == None:
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

        if "motion" in key:
            self._attr_device_info = realDevice.motionDevice
        elif "presence" in key:
            self._attr_device_info = realDevice.presenceDevice

        # 根据类型设置不同的范围和步进
        if "cycle" in key:  # 存在判断周期
            self._attr_native_min_value = 2
            self._attr_native_max_value = 30
            self._attr_native_step = 1
            self._native_value = 2
            self._attr_native_unit_of_measurement = "min"
            self._attr_device_class = NumberDeviceClass.DURATION
        elif "sensitivity" in key:  # 灵敏度
            self._attr_native_min_value = 0
            self._attr_native_max_value = 100
            self._attr_native_step = 1
            self._native_value = 50
        elif "distance" in key:  # 距离阈值 (最小/最大值)
            self._attr_native_min_value = 0
            self._attr_native_max_value = 10
            self._attr_native_step = 0.1
            if 'min' in key:
                self._native_value = 0
            elif 'max' in key:
                self._native_value = 10
            self._attr_native_unit_of_measurement = "m"
            self._attr_device_class = NumberDeviceClass.DISTANCE
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
                        value = value - 0.1
        elif "max" in self._key:
            minKey = self._key.replace('max', 'min')
            minValue = await realDevice.getKV(minKey)
            if minValue != '' and minValue != None:
                if value < float(minValue):
                    value = float(minValue)
                    if value == self._native_value:
                        value = value + 0.1
        await realDevice.setKV(self._key, str(value))
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
        self.async_on_remove(
            async_track_time_interval(self.hass, self.update_value, timedelta(seconds=1))
        )

class EnvironmentStudyButton(ButtonEntity):
    """环境学习按钮"""

    def __init__(self, on: bool):
        self._on = on
        if on:
            self._attr_name = "开启环境学习"
        else:
            self._attr_name = "关闭环境学习"
        self._attr_unique_id = f"environment_study_button_{self._on}"
        self._attr_device_info = realDevice.motionDevice

    async def async_press(self):
        await realDevice.setKV('environment_study', '1' if self._on else '0')

class EnvironmentStudySensor(BinarySensorEntity):
    """环境学习传感器"""
    def __init__(self):
        self._attr_name = "环境学习"
        self._attr_unique_id = "environment_study_status"
        self._attr_device_info = realDevice.motionDevice
        self._is_on = False
        self._attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self):
        return self._is_on
    
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._is_on = await realDevice.getKV('environment_study') == '1'
        self.schedule_update_ha_state()
        self.async_on_remove(
            async_track_time_interval(self.hass, self.update_value, timedelta(seconds=1))
        )

    async def update_value(self, now=None):
        self._is_on = await realDevice.getKV('environment_study') == '1'
        if self.hass:
            self.schedule_update_ha_state()
    
def getAllBinarySensor():
    return [MotionBinarySensor(), PresenceBinarySensor(), EnvironmentStudySensor()]

def getAllSensor():
    return [DistanceSensor("人体存在的距离", 'presence'), DistanceSensor("运动感应的距离", 'motion')]

def getAllNumber():
    return [
        SettingNumber("运动判断周期", KeyType.MOTION_CYCLE),
        SettingNumber("存在判断周期", KeyType.PRESENCE_CYCLE),
        SettingNumber("运动灵敏度", KeyType.MOTION_SENSITIVITY),
        SettingNumber("存在灵敏度", KeyType.PRESENCE_SENSITIVITY),
        SettingNumber("运动最小值", KeyType.MOTION_DISTANCE_MIN),
        SettingNumber("存在最小值", KeyType.PRESENCE_DISTANCE_MIN),
        SettingNumber("运动最大值", KeyType.MOTION_DISTANCE_MAX),
        SettingNumber("存在最大值", KeyType.PRESENCE_DISTANCE_MAX),
    ]

def getAllButton():
    return [EnvironmentStudyButton(False), EnvironmentStudyButton(True)]