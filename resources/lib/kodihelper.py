# -*- coding: utf-8 -*-

import os
import urllib
import re

from katsomo import Katsomo

import xbmc
import xbmcvfs
import xbmcgui
import xbmcplugin
from xbmcaddon import Addon

class KodiHelper(object):
    def __init__(self, base_url=None, handle=None):
        addon = self.get_addon()
        self.base_url = base_url
        self.handle = handle
        self.addon_path = xbmc.translatePath(addon.getAddonInfo('path'))
        self.addon_profile = xbmc.translatePath(addon.getAddonInfo('profile'))
        self.addon_name = addon.getAddonInfo('id')
        self.addon_version = addon.getAddonInfo('version')
        self.language = addon.getLocalizedString
        self.logging_prefix = '[%s-%s]' % (self.addon_name, self.addon_version)
        if not xbmcvfs.exists(self.addon_profile):
            xbmcvfs.mkdir(self.addon_profile)
        self.k = Katsomo(self.addon_profile, True)

    def get_addon(self):
        """Returns a fresh addon instance."""
        return Addon()

    def get_setting(self, setting_id):
        addon = self.get_addon()
        setting = addon.getSetting(setting_id)
        if setting == 'true':
            return True
        elif setting == 'false':
            return False
        else:
            return setting

    def set_setting(self, key, value):
        return self.get_addon().setSetting(key, value)

    def log(self, string):
        msg = '%s: %s' % (self.logging_prefix, string)
        xbmc.log(msg=msg, level=xbmc.LOGDEBUG)

    def dialog(self, dialog_type, heading, message=None, options=None, nolabel=None, yeslabel=None):
        dialog = xbmcgui.Dialog()
        if dialog_type == 'ok':
            dialog.ok(heading, message)
        elif dialog_type == 'yesno':
            return dialog.yesno(heading, message, nolabel=nolabel, yeslabel=yeslabel)
        elif dialog_type == 'select':
            ret = dialog.select(heading, options)
            if ret > -1:
                return ret
            else:
                return None

    def get_user_input(self, heading, hidden=False):
        keyboard = xbmc.Keyboard('', heading, hidden)
        keyboard.doModal()
        if keyboard.isConfirmed():
            query = keyboard.getText()
            self.log('User input string: %s' % query)
        else:
            query = None

        if query and len(query) > 0:
            return query
        else:
            return None

    def check_for_prerequisites(self):
        if self.set_login_credentials() and self.check_for_credentials():
            return True
        else:
            return False

    def set_login_credentials(self):
        username = self.get_setting('username')
        password = self.get_setting('password')

        if not username or not password:
                self.dialog('ok', 'Information', 'Syötä käyttäjätunnus ja salasana')
                self.get_addon().openSettings()
                #return False
        else:
            return True

    def check_for_credentials(self):
        if not self.k.get_credentials():
            self.login_process()
        return True

    def login_process(self):
        username = self.get_setting('username')
        password = self.get_setting('password')
        self.k.login(username, password)

    def reset_credentials(self):
        self.k.reset_credentials()
        self.set_setting('username', '')
        self.set_setting('password', '')

    def add_item(self, title, params, items=False, folder=True, playable=False, info=None, art=None, content=False):
        addon = self.get_addon()
        listitem = xbmcgui.ListItem(label=title)

        if playable:
            listitem.setProperty('IsPlayable', 'true')
            folder = False
        if art:
            listitem.setArt(art)
        else:
            art = {
                'icon': addon.getAddonInfo('icon'),
                'fanart': addon.getAddonInfo('fanart')
            }
            listitem.setArt(art)
        if info:
            listitem.setInfo('video', info)
        if content:
            xbmcplugin.setContent(self.handle, content)

        recursive_url = self.base_url + '?' + urllib.urlencode(params)

        if items is False:
            xbmcplugin.addDirectoryItem(self.handle, recursive_url, listitem, folder)
        else:
            items.append((recursive_url, listitem, folder))
            return items

    def eod(self):
        """Tell Kodi that the end of the directory listing is reached."""
        xbmcplugin.endOfDirectory(self.handle)

    def play_item(self, video_id):
        stream = self.k.get_stream(video_id)

        playitem = xbmcgui.ListItem(path=stream['mpd_url'])
        playitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
        playitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')

        if stream['drm_protected']:
            playitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
        playitem.setProperty('inputstream.adaptive.license_key', stream['license_url'] + '||R{SSM}|')
        xbmcplugin.setResolvedUrl(self.handle, True, listitem=playitem)

    def get_as_bool(self, string):
        if string == 'true':
            return True
        else:
            return False
