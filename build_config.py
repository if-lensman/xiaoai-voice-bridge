"""Shared Android build paths. Set JAVA_HOME and ANDROID_HOME on other machines."""
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parent
JDK=Path(os.environ.get('JAVA_HOME','/Applications/Android Studio.app/Contents/jbr/Contents/Home'))
SDK=Path(os.environ.get('ANDROID_HOME',str(Path.home()/'Library/Android/sdk')))
