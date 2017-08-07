#!/usr/bin/env python

from virtbmc import optparse
from virtbmc.optparse import get_args, get_parser
from virtbmc.clrlog import LOG
import virtbmc.manager as manager


if __name__ == '__main__':
    try:
        optparse.init()
        args = get_args()
        if args.verbose:
            import logging
            LOG.setLevel(logging.DEBUG)
            LOG.info('ARGS: {}'.format(args))
        args.func(args)
        #if args.number > 0:
        #    manager.create(args)
        #elif args.start_bmc:
        #    manager.start(args)
        #else:
        #    get_parser().print_help()

    except SystemExit as e:
        if e.code != 0:
            LOG.error(str(e))
        raise e
