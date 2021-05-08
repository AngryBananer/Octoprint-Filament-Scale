# coding=utf-8
from __future__ import absolute_import
import sys


import octoprint.plugin
import flask
import threading
from .hx711 import HX711
import RPi.GPIO as GPIO

class Filament_scalePlugin(octoprint.plugin.SettingsPlugin,
                           octoprint.plugin.AssetPlugin,
                           octoprint.plugin.TemplatePlugin,
                           octoprint.plugin.StartupPlugin,
                           octoprint.plugin.EventHandlerPlugin):


    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=True)
        ]
    
    def get_settings_defaults(self):
        return dict(
            tare = 8430152,
            reference_unit=-411,
            spool_weight=200,
            clockpin=21,
            datapin=20,
            lastknownweight=0,
            getfromgcode=1
            
            # put your plugin's default settings here
        )

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return dict(
            js=["js/filament_scale.js"],
            css=["css/filament_scale.css"],
            less=["less/filament_scale.less"]
        )

    
    def on_startup(self, host, port):
        self.hx = HX711(20, 21)
        self.hx.set_reading_format("LSB", "MSB") 
        self.hx.reset()
        self.hx.power_up()
        self.t = octoprint.util.RepeatedTimer(3.0, self.check_weight)
        self.t.start()
        
    def check_weight(self):
        self.hx.power_up()
        v = self.hx.read()
        self._plugin_manager.send_plugin_message(self._identifier, v) 
        self.hx.power_down()
        
    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
        # for details.
        return dict(
            filament_scale=dict(
                displayName="Filament Scale Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="AngryBananer",
                repo="OctoPrint-Filament-scale",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/AngryBananer/OctoPrint-Filament-scale/archive/{target_version}.zip"
            )
        )


    def on_event(self, event, payload):
        if event == Events.FILE_SELECTED:
            if self._settings.get_boolean(["getfromgcode"]):
                fileLocation = payload.get("origin")
                selectedFilename = payload.get("path")
                if (fileLocation == octoprint.filemanager.FileDestinations.LOCAL):
                    selectedFile = self._file_manager.path_on_disk(fileLocation, selectedFilename)
                    try:
                        import io
                        with io.open(selectedFile, "r", encoding="ISO-8859-1") as f:
                            for line in f:
                                if "filament_spool_weight = " in line:
                                    spool_weight_str = ""
                                for i in line:
                                    if i.isdigit() == True:
                                        spool_weight_str = spool_weight_str + i
                                self._logger.info("Extracted spool weight: " + spool_weight_str + "g")
                                self._settings.set_int(["spool_weight"], spool_weight_str)
                                self._settings.save()
                                return
                    except Exception as error:
                        errorMessage = "ERROR! File: '" + selectedFile + " Error searching spool weight. Message: '" + str(error) + "'"
                        self._logger.exception(errorMessage)
                        self._eventLogging(errorMessage)

# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Filament Scale"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = Filament_scalePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin5.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }

