import os
import logging


def mk_logger():
    try:
        import colorlog
        have_colorlog = True
    except ImportError:
        have_colorlog = False
    logger = logging.getLogger(__name__)
    format = '%(asctime)s - %(name)s[%(process)d] - ' \
        '%(filename)s[line:%(lineno)d] - [%(funcName)5s()] - %(levelname)-6s: %(message)s'
    cformat = '%(log_color)s' + format
    date_format = '%Y-%m-%d %H:%M:%S'
    f = logging.Formatter(format, date_format)
    if have_colorlog:
        cf = colorlog.ColoredFormatter(cformat, date_format,
                log_colors = {'DEBUG': 'reset', 'INFO': 'green',
                              'WARNING': 'bold_yellow', 'ERROR': 'bold_red',
                              'CRITICAL': 'bold_red'})
    else:
        cf = f
    ch = logging.StreamHandler()
    if os.isatty(2):
        ch.setFormatter(cf)
    else:
        ch.setFormatter(f)
    logger.addHandler(ch)
    return logger

LOG = mk_logger()
