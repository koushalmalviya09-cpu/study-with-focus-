[app]
title = Study Lockdown
package.name = studytracker
package.domain = org.koushal
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.2
requirements = python3==3.11.5,hostpython3==3.11.5,kivy==2.3.0,pyjnius,android
orientation = portrait
fullscreen = 1

android.archs = arm64-v8a
android.api = 34
android.ndk = 25b
p4a.branch = v2024.01.21
android.minapi = 24
android.accept_sdk_license = True
android.allow_backup = False
android.presplash_color = #0A0F1F

[buildozer]
log_level = 2
warn_on_root = 1
