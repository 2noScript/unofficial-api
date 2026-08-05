#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
DeepSeek API - Provides an unofficial API for DeepSeek by reverse-engineering its web interface.
Copyright (C) 2025 smkttl

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

import json
import base64
import struct
from wasmtime import Engine, Store, Module, Instance, Linker, WasiConfig
import wasmtime
from os import path
wasm_instance = None
wasm_current_path = None
store = None
def init_wasm(wasm_path):
    global wasm_instance, store, wasm_current_path
    if wasm_current_path != wasm_path:
        engine = Engine()
        store = Store(engine)
        with open(wasm_path, "rb") as file:
            wasm_bytes = file.read()
        module = Module(store.engine, wasm_bytes)
        linker = Linker(engine)
        wasm_instance = linker.instantiate(store, module)
        wasm_current_path = wasm_path
    return wasm_instance

def solve_wasm(algorithm, challenge, salt, expire_at, difficulty, signature, target_path, wasm_path=None):
    global store
    if wasm_path is None:
        wasm_path=path.join(path.dirname(__file__),'wasm.wasm')
    t = init_wasm(wasm_path)
    if not t:
        raise Exception("WASM module not initialized")
    difficulty = difficulty * 1.0
    n_str = f"{salt}_{expire_at}_"
    challenge_data = challenge.encode('utf-8')
    n_data = n_str.encode('utf-8')
    exports = t.exports(store)
    alloc = exports["__wbindgen_export_0"]
    stack_pointer_func = exports["__wbindgen_add_to_stack_pointer"]
    wasm_solve = exports["wasm_solve"]
    memory = exports["memory"]
    challenge_ptr = alloc(store, len(challenge_data), 1)
    n_ptr = alloc(store, len(n_data), 1)
    memory_view = memory.data_ptr(store)
    for i, byte in enumerate(challenge_data):
        memory_view[challenge_ptr + i] = byte
    for i, byte in enumerate(n_data):
        memory_view[n_ptr + i] = byte
    stack_ptr = stack_pointer_func(store, -16)
    try:
        wasm_solve(
            store,
            stack_ptr,
            challenge_ptr,
            len(challenge_data),
            n_ptr,
            len(n_data),
            difficulty
        )
        result_bytes = bytearray(16)
        for i in range(16):
            result_bytes[i] = memory_view[stack_ptr + i]
        status = struct.unpack('<i', result_bytes[0:4])[0]
        answer = struct.unpack('<d', result_bytes[8:16])[0]
        if status == 0:
            answer = None
    finally:
        stack_pointer_func(store, 16)
    if answer is not None:
        answer = int(answer)
        result_obj = {
            "algorithm": algorithm,
            "challenge": challenge,
            "salt": salt,
            "answer": answer,
            "signature": signature,
            "target_path": target_path
        }
        json_str = json.dumps(result_obj,separators=(',',':'))
        base64_str = base64.b64encode(json_str.encode('utf-8')).decode('utf-8').strip('=')
        return answer, base64_str
    return None, ""
