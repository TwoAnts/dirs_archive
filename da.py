#!/usr/bin/env python3
# -*- coding : utf-8 -*-


import os
import sys
import subprocess as sp

ARCH_MOVE = ('winrar', 'm', '-afzip', '-r', '-ibck', '-y')

def arch_move_cmd(name, arch_file_name=None):
    if not arch_file_name:
        arch_file_name = name
    cmd = []
    cmd.extend(ARCH_MOVE)
    cmd.append(arch_file_name)
    cmd.append(name)
    return cmd

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage:\n\t%s <work_dir>' %sys.argv[0])
        exit()
    work_dir = sys.argv[1]
    
    count = 0
    failed = 0
    os.chdir(work_dir)
    
    for de in os.scandir('.'):
        if de.is_dir():
            print(de.name)
    
    m = input('Above dirs is in %s, continued?(y/n):' %work_dir)
    
    if m.lower() != 'y':
        print('Cancel!')
        exit()
        
    for de in os.scandir('.'):
        if de.is_dir():
            print('in %s:' %de.path)
            os.chdir(de.path)
            for child_de in os.scandir('.'):
                if child_de.is_dir():
                    print('\tarchive %s' %child_de.name)
                    cp = sp.run(arch_move_cmd(child_de.name))
                    count += 1
                    if cp.returncode != 0:
                        failed += 1
                        print('\tFailed! %s' %cp.returncode)
            os.chdir('..')
    
    print('Done, archive %s(%s failed) dirs.' %(count, failed))
    