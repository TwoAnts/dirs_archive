#!/usr/bin/env python3
# -*- coding : utf-8 -*-


import os
import re
import sys
import shutil
import mimetypes
import subprocess as sp

ARCH_MOVE = ('winrar', 'm', '-ep1', '-afzip', '-r', '-ibck', '-y')

SSUB_PATTERN = re.compile(r'##?\S+#?#')

def arch_move_cmd(name, arch_file_name=None):
    if not arch_file_name:
        arch_file_name = name
    if not arch_file_name.endswith('.zip'):
        arch_file_name += '.zip'  #avoid some errors when winrar 
                                  #processes filenames with no ext name.
    cmd = []
    cmd.extend(ARCH_MOVE)
    cmd.append(arch_file_name)
    cmd.append(name)
    return cmd
    
def check_img_content(dir):
    img_cnt = 0
    cnt = 0
    for de in os.scandir(dir):
        cnt += 1
        if de.is_dir():
            continue
        mt = mimetypes.guess_type(de.name)[0]
        if mt and 'image' in mt:
            img_cnt += 1
    if cnt == 0:
        return False
    return (img_cnt / cnt > 0.5)
            
def subs_arch(src, dst, src_name):
    count = 0
    failed = 0
    print('in %s:' %src)
    dst_parent = os.path.join(dst, src_name)
    if not os.path.exists(dst_parent):
        print('\tmkdir %s' %dst_parent)
        os.mkdir(dst_parent)
    os.chdir(dst_parent)
    print('\tdst: %s' %dst_parent)
    for child_de in os.scandir(src):
        if child_de.is_dir():
            if SSUB_PATTERN.search(child_de.name):
                tmp_count, tmp_failed = subs_arch(child_de.path, dst_parent, child_de.name)
                count += tmp_count
                failed += tmp_failed
                continue
            
            #if not check_img_content(child_de.path):
            #    for d in os.scandir(child_de.path):
            #        print('\tmove %s' %d.path)
            #        shutil.move(d.path, '.')
            #    continue
                    
            print('\tarchive %s ' %child_de.name)
            cp = sp.run(arch_move_cmd(child_de.path, child_de.name))
            count += 1
            if cp.returncode != 0:
                failed += 1
                print('\tFailed! %s' %cp.returncode)
        elif src != dst_parent:
            print('\tmove %s' %child_de.path)
            try:
                shutil.move(child_de.path, '.')
            except Exception as e:
                print(e)
    os.chdir('..')
    return count, failed

if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        print('Usage:\n\t%s <src_dir> <dst_dir>' %sys.argv[0])
        exit()
    src_dir = sys.argv[1]
    dst_dir = sys.argv[2] if len(sys.argv) == 3 else src_dir
    
    src_dir = os.path.abspath(src_dir)
    dst_dir = os.path.abspath(dst_dir)
    
    count = 0
    failed = 0
    os.chdir(src_dir)
    
    for de in os.scandir(src_dir):
        if de.is_dir():
            print(de.name)
    
    m = input('Above dirs is in %s move to %s, continued?(y/n):' %(src_dir, dst_dir))
    
    if m.lower() != 'y':
        print('Cancel!')
        exit()
        
    if not os.path.isdir(dst_dir):
        print('mkdir %s' %dst_dir)
        os.mkdir(dst_dir)
    if not os.path.isdir(dst_dir):
        print('mkdir %s failed!' %dst_dir)
        exit(-1)
        
    for de in os.scandir(src_dir):
        if de.is_dir():
            tmp_count, tmp_failed = subs_arch(de.path, dst_dir, de.name)
            count += tmp_count
            failed += tmp_failed
        else: 
            print('skip %s' %de.path)
    
    print('Done, archive %s(%s failed) dirs.' %(count, failed))
    