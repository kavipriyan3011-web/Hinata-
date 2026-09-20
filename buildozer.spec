[app]
title = Hinata Bot
package.name = hinatabot
package.domain = org.hinata
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav,mp3,ogg
version = 0.1

requirements = python3,pygame,gTTS,google-genai,requests,urllib3,chardet,idna

orientation = portrait
fullscreen = 0

android.permissions = INTERNET, RECORD_AUDIO, WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
