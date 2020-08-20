#!/usr/bin/env python3
# -*- coding : utf-8 -*-


import os
import re
import sys
import shutil
import mimetypes
import subprocess as sp
import enum
from collections import deque

RETURN_OK = 0
RETURN_ERR = 1

class ActionType(enum.Enum):
    NO_OP = 0
    DIRECT_MOVE = enum.auto()
    ARCH_MOVE = enum.auto()
    RECUR_SCAN = enum.auto()
    
class Action:
    def __init__(self, type, src_path=None, call_args=None, call_kwargs=None):
        self.type = type
        self.src_path = src_path
        self.args = call_args or []
        self.kwargs = call_kwargs or {}

class DaContext:
    def __init__(self, src_root_dir, dst_root_dir):
        self.src_root_dir = src_root_dir
        self.dst_root_dir = dst_root_dir

ARCH_MOVE = ('winrar', 'm', '-ep1', '-afzip', '-r', '-ibck', '-y')

def no_op_func(*args, **kwargs):
    return RETURN_OK

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
    
def direct_move(src_path, dst_path):
    try:
        shutil.move(src_path, dst_path)
    except Exception as e:
        print(e)
        return RETURN_ERR
    return RETURN_OK

def arch_move(src_path, src_name, dst_dir_path):
    cwd = os.getcwd()
    os.chdir(dst_dir_path)
    cp = sp.run(arch_move_cmd(src_path, src_name))
    os.chdir(cwd)
    return cp.returncode

def check_img_content(dir):
    img_cnt = 0
    dir_cnt = 0
    cnt = 0
    for de in os.scandir(dir):
        cnt += 1
        if de.is_dir():
            dir_cnt + 1
            continue
        mt = mimetypes.guess_type(de.name)[0]
        if mt and 'image' in mt:
            img_cnt += 1
    if cnt == 0:
        return False
    return ((img_cnt / cnt >= 0.5) and (dir_cnt <= 1))
    
def get_dst_dir(ctx, src_dir):
    dst_dir = os.path.join(ctx.dst_root_dir, os.path.relpath(src_dir, ctx.src_root_dir))
    return os.path.abspath(dst_dir)

def scan_and_gen_actions(ctx, src_dir, action_list=None):
    if action_list is None:
        print ('Error: action list is None.')
        return RETURN_ERR
    
    dst_dir = get_dst_dir(ctx, src_dir)
    for de in os.scandir(src_dir):
        action = None
        if de.is_dir():
            if check_img_content(de.path):
                action = Action(ActionType.ARCH_MOVE, 
                                de.path,
                                (de.path, de.name, dst_dir))
            else:
                action = Action(ActionType.RECUR_SCAN, 
                                de.path,
                                (ctx, de.path))
        else:
            action = Action(ActionType.DIRECT_MOVE, 
                            de.path,
                            (de.path, dst_dir))
        
        if action:
            action_list.append(action)

    return RETURN_OK

ACTION_FUNC_MAP = {
    ActionType.NO_OP : no_op_func,
    ActionType.DIRECT_MOVE : direct_move,
    ActionType.ARCH_MOVE : arch_move,
    ActionType.RECUR_SCAN : scan_and_gen_actions,
}

def execute_action_deque(ctx, actions):
    fail_cnt = 0
    arch_cnt = 0
    move_cnt = 0
    new_actions = deque()
    new_action_list = []
    old_dir_path = None
    
    while new_actions or actions:
        action = None
        if new_actions:
            action = new_actions.popleft()
        else:
            action = actions.popleft()
        
        cur_dir_path = os.path.dirname(action.src_path)
        if old_dir_path != cur_dir_path:
            old_dir_path = cur_dir_path
            print('in %s:' %cur_dir_path)
            cur_dst_dir = get_dst_dir(ctx, cur_dir_path)
            if not os.path.isdir(cur_dst_dir):
                print('\tmkdir: %s' %cur_dst_dir)
                os.makedirs(cur_dst_dir)
            
            print('\tdst: %s' %get_dst_dir(ctx, cur_dir_path))
    
        print('\t%s %s' %(action.type.name, action.src_path))
    
        if action.type is ActionType.RECUR_SCAN:
            action.kwargs['action_list'] = new_action_list
        
        ret = ACTION_FUNC_MAP[action.type](*action.args, **action.kwargs)
        if RETURN_OK != ret:
            fail_cnt += 1
            print('\tFailed: %s %s %s' %(ret, action.type.name, action.src_path))
        else:
            if action.type is ActionType.DIRECT_MOVE:
                move_cnt += 1
            elif action.type is ActionType.ARCH_MOVE:
                arch_cnt += 1
                
        new_actions.extendleft(new_action_list)
        new_action_list.clear()
    
    return arch_cnt, move_cnt, fail_cnt

if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        print('Usage:\n\t%s <src_dir> <dst_dir>' %sys.argv[0])
        exit()
    src_dir = sys.argv[1]
    dst_dir = sys.argv[2]
    
    src_dir = os.path.abspath(src_dir)
    dst_dir = os.path.abspath(dst_dir)
    
    if dst_dir.startswith(src_dir) and src_dir == os.path.commonpath((src_dir, dst_dir)):
        print('Error: dst_dir is inside src_dir or same with src_dir. \nsrc_dir:%s\ndst_dir:%s'
                %(src_dir, dst_dir))
        exit()
    
    ctx = DaContext(src_dir, dst_dir)
    
    action_list = []
    
    scan_and_gen_actions(ctx, src_dir, action_list)
    
    for action in action_list:
        print ('%s %s' %(action.type.name, os.path.basename(action.src_path)))
    
    m = input('Do above actions from %s move to %s, continued?(y/n):' %(src_dir, dst_dir))
    
    if m.lower() != 'y':
        print('Cancel!')
        exit()
        
    actions = deque()
    actions.extend(action_list)
        
    arch_cnt, move_cnt, fail_cnt = execute_action_deque(ctx, actions)
    
    print('Done, arch %s, move %s, fail %s.' %(arch_cnt, move_cnt, fail_cnt))
    