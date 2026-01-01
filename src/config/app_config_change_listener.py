"""
应用配置变更监听器
专门用于监听应用相关配置的变化，例如语言设置等
"""

import locale
import logging
from typing import Optional

from .config_change_listener import (
    ConfigChangeListener,
    ConfigInitializeEvent,
)
from .config_service import config_service


class AppConfigChangeListener(ConfigChangeListener):
    """应用配置变更监听器"""

    async def onInitialize(self, event: ConfigInitializeEvent) -> None:
        """
        初始化时检测系统语言，并设置默认的应用语言
        """
        logger.info("响应配置初始化事件 - 开始检测系统语言")
        try:
            # 检查是否已经设置了语言
            existing_language = await config_service.get_setting("app.language")

            if not existing_language:
                # 如果没有设置语言，则根据系统语言自动设置
                system_language = self._detect_system_language()

                if system_language:
                    await config_service.set_setting("app.language", system_language)
                    logger.info(f"已根据系统语言设置应用语言为: {system_language}")
                else:
                    # 如果无法检测系统语言，默认使用英文
                    await config_service.set_setting("app.language", "en")
                    logger.info("无法检测系统语言，使用默认语言: en")

        except Exception as e:
            logger.error(f"检测系统语言失败: {str(e)}")
            # 发生错误时，设置默认语言
            try:
                await config_service.set_setting("app.language", "en")
            except Exception as set_error:
                logger.error(f"设置默认语言失败: {str(set_error)}")

    def _detect_system_language(self) -> Optional[str]:
        """
        检测系统语言

        Returns:
            str: 'zh' 表示中文，'en' 表示英文，None 表示无法检测
        """
        try:
            # 获取系统默认语言环境
            system_locale = locale.getdefaultlocale()[0]

            if not system_locale:
                # 如果无法获取语言环境，默认返回英文
                return "en"

            # 检查语言环境是否以 'zh' 开头（中文）
            # 例如: 'zh_CN', 'zh_TW', 'zh-Hans', 'zh-Hant' 等
            if system_locale.lower().startswith("zh"):
                return "zh"
            else:
                return "en"

        except Exception as e:
            logger.error(f"检测系统语言时出错: {str(e)}")
            return "en"


# 配置日志记录器
logger = logging.getLogger(__name__)

# 创建全局应用配置监听器实例
app_config_listener = AppConfigChangeListener()
