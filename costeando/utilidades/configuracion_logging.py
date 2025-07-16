import logging
import sys
from pathlib import Path
from platformdirs import user_log_dir
import logging.config

def configurar_logging():
    """Configura el sistema de logging para la aplicación"""
    is_compiled = getattr(sys, 'frozen', False)
    
    # Configuración base común
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(levelname)s - %(message)s'
            }
        },
        'handlers': {
            'file_handler': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'standard',
                'maxBytes': 10*1024*1024,  # 10 MB
                'backupCount': 3,
                'encoding': 'utf-8'
            },
            'error_file_handler': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'standard',
                'maxBytes': 5*1024*1024,  # 5 MB
                'backupCount': 2,
                'encoding': 'utf-8',
                'level': 'WARNING'
            }
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['file_handler', 'error_file_handler'],
                'level': 'DEBUG' if not is_compiled else 'INFO',
                'propagate': False
            }
        }
    }
    
    # Configuración específica por entorno
    if is_compiled:
        # Modo distribución/producción
        log_dir = Path(user_log_dir("ProcesadorCostos"))
        app_log = log_dir / 'procesador_costos.log'
        error_log = log_dir / 'procesador_costos_errors.log'
        
        logging_config['handlers']['file_handler'].update({
            'filename': str(app_log),
            'level': 'INFO'
        })
        logging_config['handlers']['error_file_handler']['filename'] = str(error_log)
    else:
        # Modo desarrollo
        log_dir = Path(__file__).parent / 'logs'
        app_log = log_dir / 'debug.log'
        error_log = log_dir / 'errors.log'
        
        logging_config['handlers']['file_handler'].update({
            'filename': str(app_log),
            'level': 'DEBUG'
        })
        logging_config['handlers']['error_file_handler']['filename'] = str(error_log)
        
        # Añadir consola solo en desarrollo
        logging_config['handlers']['console'] = {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'
        }
        logging_config['loggers']['']['handlers'].append('console')
    
    # Crear directorio de logs
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        # Fallback básico si falla la creación del directorio
        logging.basicConfig(level=logging.INFO)
        logging.error(f"No se pudo crear directorio de logs: {str(e)}")
        return
    
    # Aplicar configuración
    try:
        logging.config.dictConfig(logging_config)
    except Exception as e:
        logging.basicConfig(level=logging.INFO)
        logging.error(f"Error configurando logging: {str(e)}")