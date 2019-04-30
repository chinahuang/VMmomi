"""
Generated by 'django-admin startproject' using Django 1.10.4.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""
from __future__ import unicode_literals
import os
import logging
import sys
import errno
reload(sys)
sys.setdefaultencoding(u'utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)).decode(sys.getfilesystemencoding()).encode(u'utf-8'))
SECRET_KEY = u'*'
DEFAULT_LINUX_USERNAME = u'root'
DEFAULT_WIN_USERNAME = u'admin'
ES_SESSION_COOKIE_AGE = 1800
ES_SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_AGE = None
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_NAME = u'csrf_exempt'
CSRF_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_HTTPONLY = True
CSP_DEFAULT_SRC = (u"'self'",)
CSP_STYLE_SRC = (u"'self'", u"'unsafe-inline'", u"'unsafe-eval'", u'https://127.0.0.1')
CSP_SCRIPT_SRC = (u"'self'", u"'unsafe-inline'", u"'unsafe-eval'", u'https://127.0.0.1')
CSP_FONT_SRC = u"'self'"
CSP_IMG_SRC = (u"'self'", u"'unsafe-inline'", u"'unsafe-eval'", u'https://127.0.0.1', u'data:')
DEBUG = False
ALLOWED_HOSTS = [u'localhost', u'127.0.0.1']
INSTALLED_APPS = [u'authx',
 u'django.contrib.auth',
 u'django.contrib.contenttypes',
 u'django.contrib.sessions',
 u'django.contrib.messages',
 u'django.contrib.staticfiles',
 u'sslserver',
 u'dashboard',
 u'taskmgr',
 u'objectmgr']
PASSWD_MIN_LENGTH = 10
PASSWD_MAX_LENGTH = 32
PASSWORD_COMPLEXITY = {u'UPPER': 1,
 u'LOWER': 1,
 u'DIGITS': 1,
 u'SPECIAL': 1}
MIDDLEWARE_CLASSES = [u'django.middleware.security.SecurityMiddleware',
 u'django.middleware.common.CommonMiddleware',
 u'django.contrib.sessions.middleware.SessionMiddleware',
 u'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
 u'django.contrib.auth.middleware.AuthenticationMiddleware',
 u'django.contrib.messages.middleware.MessageMiddleware',
 u'django.middleware.clickjacking.XFrameOptionsMiddleware',
 u'django.middleware.csrf.CsrfViewMiddleware',
 u'es_midware.es_midware.CSPMiddleware']
ROOT_URLCONF = u'easysuite.urls'
TEMPLATES = [{u'BACKEND': u'django.template.backends.django.DjangoTemplates',
  u'DIRS': [os.path.join(BASE_DIR, u'dashboard', u'templates')],
  u'APP_DIRS': True,
  u'OPTIONS': {u'context_processors': [u'django.template.context_processors.debug',
                                       u'django.template.context_processors.request',
                                       u'django.contrib.auth.context_processors.auth',
                                       u'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = u'easysuite.wsgi.application'
DATABASES = {u'default': {u'ENGINE': u'django.db.backends.sqlite3',
              u'NAME': os.path.join(BASE_DIR, u'db', u'easysuite.sqlite3')}}
AUTH_PASSWORD_VALIDATORS = [{u'NAME': u'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
 {u'NAME': u'django.contrib.auth.password_validation.MinimumLengthValidator'},
 {u'NAME': u'django.contrib.auth.password_validation.CommonPasswordValidator'},
 {u'NAME': u'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANG = u'zh_CN'
I18N_APPS = [u'dashboard', u'taskmgr', u'objectmgr']
LANGUAGE_CODE = u'zh-hans'
TIME_ZONE = u'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
STATIC_URL = u'/static/'
STATIC_ROOT = os.path.join(BASE_DIR, u'dashboard/static').replace(u'\\', u'/')
LOGIN_REDIRECT_URL = u'/dashboard/'
COMMON_CFG_DIR = os.path.join(BASE_DIR, u'plugins\\common').replace(u'\\', u'/')
PKG_CFG_DIR = os.path.join(BASE_DIR, u'plugins').replace(u'\\', u'/')
IPMITOOL_DIR = os.path.join(BASE_DIR, u'3rdparty\\ipmitool\\Windows').replace(u'\\', u'/')
PXETOOL_DIR = os.path.join(BASE_DIR, u'3rdparty\\pxetool').replace(u'\\', u'/')
TFTPD64_DIR = os.path.join(BASE_DIR, u'3rdparty\\tftpd64').replace(u'\\', u'/')
ZIP7_DIR = os.path.join(BASE_DIR, u'3rdparty\\7zip').replace(u'\\', u'/')
VER_TOOL_DIR = os.path.join(BASE_DIR, u'3rdparty\\VerificationTools').replace(u'\\', u'/')
WINPE_ISO_DIR = os.path.join(BASE_DIR, u'3rdparty\\winpe').replace(u'\\', u'/')
SYS_LINUX_DIR = os.path.join(BASE_DIR, u'3rdparty\\syslinux').replace(u'\\', u'/')
VAR_DIR = os.path.join(os.path.dirname(BASE_DIR), u'var').replace(u'\\', u'/')
ROOT_EXPORT_FILE_DIR = os.path.join(VAR_DIR, u'export').replace(u'\\', u'/')
FTP_ROOT_DIR = os.path.join(VAR_DIR, u'software').replace(u'\\', u'/')
MIGRATE_ROOT_DTR = os.path.join(VAR_DIR, u'temp', u'migrate').replace(u'\\', u'/')
MIGRATE_ASSESS_DIR = os.path.join(VAR_DIR, u'temp', u'migrate_log', u'var', u'assess').replace(u'\\', u'/')
LOG_ROOT_DIR = os.path.join(VAR_DIR, u'run\\log').replace(u'\\', u'/')
LOG_DETAIL_ROOT_DIR = os.path.join(VAR_DIR, u'run\\log\\vmware').replace(u'\\', u'/')
TEMP_DIR = os.path.join(VAR_DIR, u'temp').replace(u'\\', u'/')
PXE_BOOT_DIR = os.path.join(VAR_DIR, u'temp\\pxe').replace(u'\\', u'/')
PXE_FTP_DIR = os.path.join(VAR_DIR, u'temp\\ftp').replace(u'\\', u'/')
PXE_PXELINUX_CFG_DIR = os.path.join(VAR_DIR, u'temp\\pxe\\pxelinux.cfg').replace(u'\\', u'/')
TASK_REPORT_DIR = os.path.join(VAR_DIR, u'run\\report').replace(u'\\', u'/')
SECURITY_DIR = os.path.join(VAR_DIR, u'.easysuite').replace(u'\\', u'/')
CERTS_PATH = os.path.join(BASE_DIR, u'certs').replace(u'\\', u'/')
DEFAULT_CONFIG = os.path.join(BASE_DIR, u'easysuite\\config\\default_config.properties').replace(u'\\', u'/')
TASKMGR_PATH = os.path.join(BASE_DIR, u'taskmgr').replace(u'\\', u'/')
REMOTE_PACKAGE_DIR = u'/opt/easysuite'
REMOTE_PACKAGE_UNZIP_DIR = u'/opt/install'
REMOTE_PACKAGE_MIGRATE_DIR = u'/opt/migrate'
REMOTE_PACKAGE_MIGRATE_LOG_DIR = u'/opt/migrate_log'
OS_TOOL_DIR = os.path.join(BASE_DIR, u'tools\\osconfig').replace(u'\\', u'/')
VM_TOOL_DIR = os.path.join(BASE_DIR, u'tools\\vmconfig').replace(u'\\', u'/')
ESXI_TOOL_DIR = os.path.join(BASE_DIR, u'tools\\vmconfig\\esxi').replace(u'\\', u'/')
VCENTER_TOOL_DIR = os.path.join(BASE_DIR, u'tools\\vmconfig\\vcsa').replace(u'\\', u'/')
BOND_TOOL_DIR = os.path.join(BASE_DIR, u'tools\\osconfig\\bond_tools').replace(u'\\', u'/')
COMMON_TOOL_DIR = os.path.join(BASE_DIR, u'tools\\osconfig\\common_tools').replace(u'\\', u'/')
LOG_LEVEL = logging.INFO
OPERATE_LOG_TYPE = 1
SECURITY_LOG_TYPE = 2
SYSYTEM_LOG_TYPE = 3
MIGRATE_PACKAGE = u'NCEV100R018C10_EasySuite_Migrate.zip'
MIGRATE_ASSESS_PACKAGE = u'NCEV100R018C10_Easysuite_Migrate_Assess.zip'
LOGGING = {u'version': 1,
 u'disable_existing_loggers': False,
 u'formatters': {u'detail': {u'format': u'[%(asctime)s][%(filename)s][line:%(lineno)d][%(levelname)s] %(message)s',
                             u'datefmt': u'%Y-%m-%d %H:%M:%S'}},
 u'handlers': {u'file': {u'level': u'INFO',
                         u'class': u'logging.FileHandler',
                         u'formatter': u'detail',
                         u'filename': os.path.join(LOG_ROOT_DIR, u'easysuite.log')},
               u'file2': {u'level': u'ERROR',
                          u'class': u'logging.FileHandler',
                          u'formatter': u'detail',
                          u'filename': os.path.join(LOG_ROOT_DIR, u'easysuite.log')},
               u'file3': {u'level': u'WARNING',
                          u'class': u'logging.FileHandler',
                          u'formatter': u'detail',
                          u'filename': os.path.join(LOG_ROOT_DIR, u'easysuite.log')},
               u'console': {u'level': u'INFO',
                            u'class': u'logging.StreamHandler'}},
 u'loggers': {u'dashboard': {u'handlers': [u'file', u'console'],
                             u'level': u'INFO',
                             u'propagate': True},
              u'usermgr': {u'handlers': [u'file', u'console'],
                           u'level': u'INFO',
                           u'propagate': True},
              u'sslserver': {u'handlers': [u'file', u'console'],
                             u'level': u'INFO',
                             u'propagate': True},
              u'taskmgr': {u'handlers': [u'file', u'console'],
                           u'level': u'INFO',
                           u'propagate': True},
              u'objectmgr': {u'handlers': [u'file', u'console'],
                             u'level': u'INFO',
                             u'propagate': True},
              u'plugins': {u'handlers': [u'file', u'console'],
                           u'level': u'INFO',
                           u'propagate': True},
              u'utils': {u'handlers': [u'file', u'console'],
                         u'level': u'INFO',
                         u'propagate': True}}}
TASK_FINISH_PREDICT_TIME = u'60'
TASKTOTAL_TIME = 60

def __make_dirs():
    path_list = [FTP_ROOT_DIR,
     LOG_DETAIL_ROOT_DIR,
     LOG_ROOT_DIR,
     PKG_CFG_DIR,
     PXE_BOOT_DIR,
     PXE_FTP_DIR,
     PXE_PXELINUX_CFG_DIR,
     ROOT_EXPORT_FILE_DIR,
     TASK_REPORT_DIR,
     TEMP_DIR,
     SECURITY_DIR,
     MIGRATE_ROOT_DTR,
     MIGRATE_ASSESS_DIR]
    for path in path_list:
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
                print u'Create directory -> %s' % path
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                else:
                    raise


def __create_integrity_flagfile():
    integrity_log = os.path.join(LOG_ROOT_DIR, u'integrity.log')
    f = open(integrity_log, u'w')
    f.close()


__make_dirs()
__create_integrity_flagfile()
