(module
  (type (;0;) (func (param i32 i32 i32) (result i32)))
  (type (;1;) (func (param i32)))
  (type (;2;) (func (param i32) (result i32)))
  (type (;3;) (func (param i32 i32 i32 i32) (result i32)))
  (type (;4;) (func (param i32 i32) (result i32)))
  (type (;5;) (func (param i32 i32 i32 i32 i32 i32) (result i32)))
  (type (;6;) (func (param i32 i32 i32 i32 i32) (result i32)))
  (type (;7;) (func))
  (type (;8;) (func (result i32)))
  (type (;9;) (func (param i32 i64 i32) (result i64)))
  (type (;10;) (func (param i32 i32 i32 i32)))
  (import "env" "putc_js" (func $putc_js (type 1)))
  (import "env" "__syscall0" (func $__syscall0 (type 2)))
  (import "env" "__syscall3" (func $__syscall3 (type 3)))
  (import "env" "__syscall1" (func $__syscall1 (type 4)))
  (import "env" "__syscall5" (func $__syscall5 (type 5)))
  (import "env" "__syscall4" (func $__syscall4 (type 6)))
  (func $__wasm_call_ctors (type 7))
  (func $main (type 8) (result i32)
    i32.const 1024
    call $puts
    drop
    i32.const 0)
  (func $writev_c (type 0) (param i32 i32 i32) (result i32)
    (local i32 i32 i32 i32 i32 i32)
    block  ;; label = @1
      local.get 2
      i32.const 1
      i32.lt_s
      br_if 0 (;@1;)
      i32.const 0
      local.set 3
      i32.const 0
      local.set 4
      loop  ;; label = @2
        i32.const 0
        local.set 5
        block  ;; label = @3
          local.get 1
          local.get 3
          i32.const 3
          i32.shl
          i32.add
          local.tee 6
          i32.load offset=4
          i32.eqz
          br_if 0 (;@3;)
          local.get 6
          i32.const 4
          i32.add
          local.set 7
          i32.const 0
          local.set 8
          loop  ;; label = @4
            local.get 6
            i32.load
            local.get 8
            i32.add
            i32.load8_s
            call $putc_js
            local.get 8
            i32.const 1
            i32.add
            local.tee 8
            local.get 7
            i32.load
            local.tee 5
            i32.lt_u
            br_if 0 (;@4;)
          end
        end
        local.get 5
        local.get 4
        i32.add
        local.set 4
        local.get 3
        i32.const 1
        i32.add
        local.tee 3
        local.get 2
        i32.ne
        br_if 0 (;@2;)
      end
      local.get 4
      return
    end
    i32.const 0)
  (func $__errno_location (type 8) (result i32)
    i32.const 39)
  (func $__syscall_ret (type 2) (param i32) (result i32)
    block  ;; label = @1
      local.get 0
      i32.const -4095
      i32.lt_u
      br_if 0 (;@1;)
      call $__errno_location
      i32.const 0
      local.get 0
      i32.sub
      i32.store
      i32.const -1
      local.set 0
    end
    local.get 0)
  (func $__lockfile (type 2) (param i32) (result i32)
    (local i32 i32 i32)
    i32.const 0
    local.set 1
    block  ;; label = @1
      i32.const 0
      i32.load offset=27
      local.tee 2
      local.get 0
      i32.load offset=76
      i32.eq
      br_if 0 (;@1;)
      block  ;; label = @2
        local.get 0
        i32.const 76
        i32.add
        local.tee 1
        i32.load
        local.tee 3
        i32.eqz
        br_if 0 (;@2;)
        local.get 0
        i32.const 80
        i32.add
        local.set 0
        loop  ;; label = @3
          local.get 1
          local.get 0
          local.get 3
          i32.const 1
          call $__wait
          local.get 1
          i32.load
          local.tee 3
          br_if 0 (;@3;)
        end
      end
      local.get 1
      local.get 2
      i32.store
      i32.const 1
      local.set 1
    end
    local.get 1)
  (func $__unlockfile (type 1) (param i32)
    i32.const 375
    call $__syscall0
    call $__syscall_ret
    drop
    local.get 0
    i32.const 0
    i32.store offset=76
    i32.const 375
    call $__syscall0
    call $__syscall_ret
    drop
    block  ;; label = @1
      local.get 0
      i32.load offset=80
      i32.eqz
      br_if 0 (;@1;)
      i32.const 240
      local.get 0
      i32.const 76
      i32.add
      local.tee 0
      i32.const 129
      i32.const 1
      call $__syscall3
      i32.const -38
      i32.ne
      br_if 0 (;@1;)
      i32.const 240
      local.get 0
      i32.const 1
      i32.const 1
      call $__syscall3
      drop
    end)
  (func $__towrite (type 2) (param i32) (result i32)
    (local i32)
    local.get 0
    local.get 0
    i32.load8_u offset=74
    local.tee 1
    i32.const -1
    i32.add
    local.get 1
    i32.or
    i32.store8 offset=74
    block  ;; label = @1
      local.get 0
      i32.load
      local.tee 1
      i32.const 8
      i32.and
      br_if 0 (;@1;)
      local.get 0
      i64.const 0
      i64.store offset=4 align=4
      local.get 0
      local.get 0
      i32.load offset=44
      local.tee 1
      i32.store offset=28
      local.get 0
      local.get 1
      i32.store offset=20
      local.get 0
      local.get 1
      local.get 0
      i32.load offset=48
      i32.add
      i32.store offset=16
      i32.const 0
      return
    end
    local.get 0
    local.get 1
    i32.const 32
    i32.or
    i32.store
    i32.const -1)
  (func $fwrite (type 3) (param i32 i32 i32 i32) (result i32)
    (local i32 i32 i32 i32 i32 i32 i32 i32)
    i32.const 0
    local.set 4
    block  ;; label = @1
      local.get 3
      i32.load offset=76
      i32.const 0
      i32.lt_s
      br_if 0 (;@1;)
      local.get 3
      call $__lockfile
      i32.const 0
      i32.ne
      local.set 4
    end
    local.get 2
    local.get 1
    i32.mul
    local.set 5
    block  ;; label = @1
      block  ;; label = @2
        block  ;; label = @3
          block  ;; label = @4
            block  ;; label = @5
              block  ;; label = @6
                local.get 3
                i32.load offset=16
                local.tee 6
                i32.eqz
                br_if 0 (;@6;)
                local.get 6
                local.get 3
                i32.load offset=20
                local.tee 7
                i32.sub
                local.get 5
                i32.ge_u
                br_if 1 (;@5;)
                br 3 (;@3;)
              end
              i32.const 0
              local.set 6
              local.get 3
              call $__towrite
              br_if 1 (;@4;)
              local.get 3
              i32.const 16
              i32.add
              i32.load
              local.get 3
              i32.load offset=20
              local.tee 7
              i32.sub
              local.get 5
              i32.lt_u
              br_if 2 (;@3;)
            end
            i32.const 0
            local.set 8
            block  ;; label = @5
              block  ;; label = @6
                local.get 3
                i32.load8_s offset=75
                i32.const 0
                i32.lt_s
                br_if 0 (;@6;)
                local.get 0
                local.get 5
                i32.add
                local.set 9
                i32.const 0
                local.set 8
                i32.const 0
                local.set 6
                loop  ;; label = @7
                  local.get 5
                  local.get 6
                  i32.add
                  i32.eqz
                  br_if 1 (;@6;)
                  local.get 9
                  local.get 6
                  i32.add
                  local.set 10
                  local.get 6
                  i32.const -1
                  i32.add
                  local.tee 11
                  local.set 6
                  local.get 10
                  i32.const -1
                  i32.add
                  i32.load8_u
                  i32.const 10
                  i32.ne
                  br_if 0 (;@7;)
                end
                local.get 3
                local.get 0
                local.get 5
                local.get 11
                i32.add
                i32.const 1
                i32.add
                local.tee 8
                local.get 3
                i32.load offset=36
                call_indirect (type 0)
                local.tee 6
                local.get 8
                i32.lt_u
                br_if 2 (;@4;)
                local.get 11
                i32.const -1
                i32.xor
                local.set 6
                local.get 9
                local.get 11
                i32.add
                i32.const 1
                i32.add
                local.set 0
                local.get 3
                i32.const 20
                i32.add
                i32.load
                local.set 7
                br 1 (;@5;)
              end
              local.get 5
              local.set 6
            end
            local.get 7
            local.get 0
            local.get 6
            call $memcpy
            drop
            local.get 3
            i32.const 20
            i32.add
            local.tee 10
            local.get 10
            i32.load
            local.get 6
            i32.add
            i32.store
            local.get 8
            local.get 6
            i32.add
            local.set 6
          end
          local.get 4
          i32.eqz
          br_if 2 (;@1;)
          br 1 (;@2;)
        end
        local.get 3
        local.get 0
        local.get 5
        local.get 3
        i32.load offset=36
        call_indirect (type 0)
        local.set 6
        local.get 4
        i32.eqz
        br_if 1 (;@1;)
      end
      local.get 3
      call $__unlockfile
    end
    block  ;; label = @1
      local.get 6
      local.get 5
      i32.ne
      br_if 0 (;@1;)
      local.get 2
      i32.const 0
      local.get 1
      select
      return
    end
    local.get 6
    local.get 1
    i32.div_u)
  (func $fputs (type 4) (param i32 i32) (result i32)
    (local i32)
    i32.const -1
    i32.const 0
    local.get 0
    call $strlen
    local.tee 2
    local.get 0
    i32.const 1
    local.get 2
    local.get 1
    call $fwrite
    i32.ne
    select)
  (func $__overflow (type 4) (param i32 i32) (result i32)
    (local i32 i32 i32)
    global.get 0
    i32.const 16
    i32.sub
    local.tee 2
    global.set 0
    local.get 2
    local.get 1
    i32.store8 offset=15
    block  ;; label = @1
      block  ;; label = @2
        block  ;; label = @3
          block  ;; label = @4
            local.get 0
            i32.load offset=16
            local.tee 3
            i32.eqz
            br_if 0 (;@4;)
            local.get 0
            i32.load offset=20
            local.tee 4
            local.get 3
            i32.ge_u
            br_if 2 (;@2;)
            br 1 (;@3;)
          end
          i32.const -1
          local.set 3
          local.get 0
          call $__towrite
          br_if 2 (;@1;)
          local.get 0
          i32.load offset=20
          local.tee 4
          local.get 0
          i32.const 16
          i32.add
          i32.load
          i32.ge_u
          br_if 1 (;@2;)
        end
        local.get 1
        i32.const 255
        i32.and
        local.tee 3
        local.get 0
        i32.load8_s offset=75
        i32.eq
        br_if 0 (;@2;)
        local.get 0
        i32.const 20
        i32.add
        local.get 4
        i32.const 1
        i32.add
        i32.store
        local.get 4
        local.get 1
        i32.store8
        local.get 2
        i32.const 16
        i32.add
        global.set 0
        local.get 3
        return
      end
      i32.const -1
      local.set 3
      local.get 0
      local.get 2
      i32.const 15
      i32.add
      i32.const 1
      local.get 0
      i32.load offset=36
      call_indirect (type 0)
      i32.const 1
      i32.ne
      br_if 0 (;@1;)
      local.get 2
      i32.load8_u offset=15
      local.set 3
    end
    local.get 2
    i32.const 16
    i32.add
    global.set 0
    local.get 3)
  (func $puts (type 2) (param i32) (result i32)
    (local i32 i32)
    i32.const 0
    local.set 1
    block  ;; label = @1
      i32.const 0
      i32.load offset=1184
      local.tee 2
      i32.load offset=76
      i32.const 0
      i32.lt_s
      br_if 0 (;@1;)
      local.get 2
      call $__lockfile
      local.set 1
    end
    block  ;; label = @1
      block  ;; label = @2
        block  ;; label = @3
          local.get 0
          local.get 2
          call $fputs
          i32.const 0
          i32.lt_s
          br_if 0 (;@3;)
          block  ;; label = @4
            local.get 2
            i32.load8_u offset=75
            i32.const 10
            i32.eq
            br_if 0 (;@4;)
            local.get 2
            i32.load offset=20
            local.tee 0
            local.get 2
            i32.load offset=16
            i32.ge_u
            br_if 0 (;@4;)
            local.get 2
            i32.const 20
            i32.add
            local.get 0
            i32.const 1
            i32.add
            i32.store
            local.get 0
            i32.const 10
            i32.store8
            i32.const 0
            local.set 0
            local.get 1
            br_if 2 (;@2;)
            br 3 (;@1;)
          end
          local.get 2
          i32.const 10
          call $__overflow
          i32.const 31
          i32.shr_s
          local.set 0
          local.get 1
          i32.eqz
          br_if 2 (;@1;)
          br 1 (;@2;)
        end
        i32.const -1
        local.set 0
        local.get 1
        i32.eqz
        br_if 1 (;@1;)
      end
      local.get 2
      call $__unlockfile
    end
    local.get 0)
  (func $dummy (type 2) (param i32) (result i32)
    local.get 0)
  (func $__stdio_close (type 2) (param i32) (result i32)
    i32.const 6
    local.get 0
    i32.load offset=60
    call $dummy
    call $__syscall1
    call $__syscall_ret)
  (func $__stdio_write (type 0) (param i32 i32 i32) (result i32)
    (local i32 i32 i32 i32 i32 i32 i32)
    global.get 0
    i32.const 16
    i32.sub
    local.tee 3
    global.set 0
    local.get 3
    local.get 1
    i32.store offset=8
    local.get 3
    local.get 2
    i32.store offset=12
    local.get 3
    local.get 0
    i32.load offset=28
    local.tee 1
    i32.store
    local.get 3
    local.get 0
    i32.load offset=20
    local.get 1
    i32.sub
    local.tee 1
    i32.store offset=4
    i32.const 2
    local.set 4
    block  ;; label = @1
      block  ;; label = @2
        block  ;; label = @3
          local.get 1
          local.get 2
          i32.add
          local.tee 5
          i32.const 146
          local.get 0
          i32.load offset=60
          local.get 3
          i32.const 2
          call $__syscall3
          call $__syscall_ret
          local.tee 6
          i32.eq
          br_if 0 (;@3;)
          local.get 3
          local.set 1
          local.get 0
          i32.const 60
          i32.add
          local.set 7
          loop  ;; label = @4
            local.get 6
            i32.const -1
            i32.le_s
            br_if 2 (;@2;)
            local.get 1
            i32.const 8
            i32.add
            local.get 1
            local.get 6
            local.get 1
            i32.load offset=4
            local.tee 8
            i32.gt_u
            local.tee 9
            select
            local.tee 1
            local.get 1
            i32.load
            local.get 6
            local.get 8
            i32.const 0
            local.get 9
            select
            i32.sub
            local.tee 8
            i32.add
            i32.store
            local.get 1
            local.get 1
            i32.load offset=4
            local.get 8
            i32.sub
            i32.store offset=4
            local.get 5
            local.get 6
            i32.sub
            local.set 5
            i32.const 146
            local.get 7
            i32.load
            local.get 1
            local.get 4
            local.get 9
            i32.sub
            local.tee 4
            call $__syscall3
            call $__syscall_ret
            local.tee 9
            local.set 6
            local.get 5
            local.get 9
            i32.ne
            br_if 0 (;@4;)
          end
        end
        local.get 0
        i32.const 28
        i32.add
        local.get 0
        i32.load offset=44
        local.tee 1
        i32.store
        local.get 0
        i32.const 20
        i32.add
        local.get 1
        i32.store
        local.get 0
        local.get 1
        local.get 0
        i32.load offset=48
        i32.add
        i32.store offset=16
        local.get 2
        local.set 6
        br 1 (;@1;)
      end
      local.get 0
      i64.const 0
      i64.store offset=16
      i32.const 0
      local.set 6
      local.get 0
      i32.const 28
      i32.add
      i32.const 0
      i32.store
      local.get 0
      local.get 0
      i32.load
      i32.const 32
      i32.or
      i32.store
      local.get 4
      i32.const 2
      i32.eq
      br_if 0 (;@1;)
      local.get 1
      i32.load offset=4
      local.set 1
      local.get 3
      i32.const 16
      i32.add
      global.set 0
      local.get 2
      local.get 1
      i32.sub
      return
    end
    local.get 3
    i32.const 16
    i32.add
    global.set 0
    local.get 6)
  (func $__stdout_write (type 0) (param i32 i32 i32) (result i32)
    (local i32)
    global.get 0
    i32.const 16
    i32.sub
    local.tee 3
    global.set 0
    local.get 0
    i32.const 1
    i32.store offset=36
    block  ;; label = @1
      local.get 0
      i32.load8_u
      i32.const 64
      i32.and
      br_if 0 (;@1;)
      i32.const 54
      local.get 0
      i32.load offset=60
      i32.const 21523
      local.get 3
      i32.const 8
      i32.add
      call $__syscall3
      i32.eqz
      br_if 0 (;@1;)
      local.get 0
      i32.const 255
      i32.store8 offset=75
    end
    local.get 0
    local.get 1
    local.get 2
    call $__stdio_write
    local.set 0
    local.get 3
    i32.const 16
    i32.add
    global.set 0
    local.get 0)
  (func $__stdio_seek (type 9) (param i32 i64 i32) (result i64)
    (local i32)
    global.get 0
    i32.const 16
    i32.sub
    local.tee 3
    global.set 0
    block  ;; label = @1
      i32.const 140
      local.get 0
      i32.load offset=60
      local.get 1
      i64.const 32
      i64.shr_u
      i32.wrap_i64
      local.get 1
      i32.wrap_i64
      local.get 3
      i32.const 8
      i32.add
      local.get 2
      call $__syscall5
      call $__syscall_ret
      i32.const 0
      i32.lt_s
      br_if 0 (;@1;)
      local.get 3
      i64.load offset=8
      local.set 1
      local.get 3
      i32.const 16
      i32.add
      global.set 0
      local.get 1
      return
    end
    local.get 3
    i64.const -1
    i64.store offset=8
    local.get 3
    i32.const 16
    i32.add
    global.set 0
    i64.const -1)
  (func $memcpy (type 0) (param i32 i32 i32) (result i32)
    (local i32 i32 i32 i32 i32 i32 i32 i32)
    block  ;; label = @1
      block  ;; label = @2
        block  ;; label = @3
          block  ;; label = @4
            local.get 2
            i32.eqz
            br_if 0 (;@4;)
            local.get 1
            i32.const 3
            i32.and
            i32.eqz
            br_if 0 (;@4;)
            local.get 0
            local.set 3
            block  ;; label = @5
              loop  ;; label = @6
                local.get 3
                local.get 1
                i32.load8_u
                i32.store8
                local.get 2
                i32.const -1
                i32.add
                local.set 4
                local.get 3
                i32.const 1
                i32.add
                local.set 3
                local.get 1
                i32.const 1
                i32.add
                local.set 1
                local.get 2
                i32.const 1
                i32.eq
                br_if 1 (;@5;)
                local.get 4
                local.set 2
                local.get 1
                i32.const 3
                i32.and
                br_if 0 (;@6;)
              end
            end
            local.get 3
            i32.const 3
            i32.and
            i32.eqz
            br_if 1 (;@3;)
            br 2 (;@2;)
          end
          local.get 2
          local.set 4
          local.get 0
          local.tee 3
          i32.const 3
          i32.and
          br_if 1 (;@2;)
        end
        block  ;; label = @3
          block  ;; label = @4
            block  ;; label = @5
              local.get 4
              i32.const 16
              i32.lt_u
              br_if 0 (;@5;)
              local.get 3
              local.get 4
              i32.const -16
              i32.add
              local.tee 5
              i32.const -16
              i32.and
              local.tee 7
              i32.const 16
              i32.add
              local.tee 6
              i32.add
              local.set 8
              local.get 1
              local.set 2
              loop  ;; label = @6
                local.get 3
                local.get 2
                i32.load
                i32.store
                local.get 3
                i32.const 4
                i32.add
                local.get 2
                i32.const 4
                i32.add
                i32.load
                i32.store
                local.get 3
                i32.const 8
                i32.add
                local.get 2
                i32.const 8
                i32.add
                i32.load
                i32.store
                local.get 3
                i32.const 12
                i32.add
                local.get 2
                i32.const 12
                i32.add
                i32.load
                i32.store
                local.get 3
                i32.const 16
                i32.add
                local.set 3
                local.get 2
                i32.const 16
                i32.add
                local.set 2
                local.get 4
                i32.const -16
                i32.add
                local.tee 4
                i32.const 15
                i32.gt_u
                br_if 0 (;@6;)
              end
              local.get 1
              local.get 6
              i32.add
              local.set 1
              i32.const 8
              local.set 3
              local.get 5
              local.get 7
              i32.sub
              local.tee 4
              i32.const 8
              i32.and
              br_if 1 (;@4;)
              br 2 (;@3;)
            end
            local.get 3
            local.set 8
            i32.const 8
            local.set 3
            local.get 4
            i32.const 8
            i32.and
            i32.eqz
            br_if 1 (;@3;)
          end
          local.get 8
          local.get 1
          i32.load
          i32.store
          local.get 8
          local.get 1
          i32.load offset=4
          i32.store offset=4
          local.get 1
          local.get 3
          i32.add
          local.set 1
          local.get 8
          local.get 3
          i32.add
          local.set 8
        end
        block  ;; label = @3
          block  ;; label = @4
            block  ;; label = @5
              block  ;; label = @6
                local.get 4
                i32.const 4
                i32.and
                br_if 0 (;@6;)
                i32.const 2
                local.set 3
                local.get 4
                i32.const 2
                i32.and
                br_if 1 (;@5;)
                br 2 (;@4;)
              end
              local.get 8
              local.get 1
              i32.load
              i32.store
              local.get 1
              i32.const 4
              i32.add
              local.set 1
              local.get 8
              i32.const 4
              i32.add
              local.set 8
              i32.const 2
              local.set 3
              local.get 4
              i32.const 2
              i32.and
              i32.eqz
              br_if 1 (;@4;)
            end
            local.get 8
            local.get 1
            i32.load8_u
            i32.store8
            local.get 8
            local.get 1
            i32.load8_u offset=1
            i32.store8 offset=1
            local.get 8
            local.get 3
            i32.add
            local.set 8
            local.get 1
            local.get 3
            i32.add
            local.set 1
            local.get 4
            i32.const 1
            i32.and
            br_if 1 (;@3;)
            br 3 (;@1;)
          end
          local.get 4
          i32.const 1
          i32.and
          i32.eqz
          br_if 2 (;@1;)
        end
        local.get 8
        local.get 1
        i32.load8_u
        i32.store8
        local.get 0
        return
      end
      block  ;; label = @2
        block  ;; label = @3
          block  ;; label = @4
            block  ;; label = @5
              block  ;; label = @6
                block  ;; label = @7
                  block  ;; label = @8
                    block  ;; label = @9
                      block  ;; label = @10
                        block  ;; label = @11
                          block  ;; label = @12
                            block  ;; label = @13
                              local.get 4
                              i32.const 32
                              i32.lt_u
                              br_if 0 (;@13;)
                              local.get 3
                              i32.const 3
                              i32.and
                              local.tee 2
                              i32.const 3
                              i32.eq
                              br_if 1 (;@12;)
                              local.get 2
                              i32.const 2
                              i32.eq
                              br_if 2 (;@11;)
                              local.get 2
                              i32.const 1
                              i32.ne
                              br_if 0 (;@13;)
                              local.get 3
                              local.get 1
                              i32.load8_u offset=1
                              i32.store8 offset=1
                              local.get 3
                              local.get 1
                              i32.load
                              local.tee 5
                              i32.store8
                              local.get 3
                              local.get 1
                              i32.load8_u offset=2
                              i32.store8 offset=2
                              local.get 1
                              i32.const 16
                              i32.add
                              local.set 2
                              local.get 4
                              i32.const -19
                              i32.add
                              local.set 6
                              local.get 4
                              i32.const -3
                              i32.add
                              local.set 7
                              local.get 3
                              i32.const 3
                              i32.add
                              local.set 8
                              local.get 1
                              local.get 4
                              i32.const -20
                              i32.add
                              i32.const -16
                              i32.and
                              local.tee 9
                              i32.const 19
                              i32.add
                              local.tee 10
                              i32.add
                              local.set 1
                              loop  ;; label = @14
                                local.get 8
                                local.get 2
                                i32.const -12
                                i32.add
                                i32.load
                                local.tee 4
                                i32.const 8
                                i32.shl
                                local.get 5
                                i32.const 24
                                i32.shr_u
                                i32.or
                                i32.store
                                local.get 8
                                i32.const 4
                                i32.add
                                local.get 2
                                i32.const -8
                                i32.add
                                i32.load
                                local.tee 5
                                i32.const 8
                                i32.shl
                                local.get 4
                                i32.const 24
                                i32.shr_u
                                i32.or
                                i32.store
                                local.get 8
                                i32.const 8
                                i32.add
                                local.get 2
                                i32.const -4
                                i32.add
                                i32.load
                                local.tee 4
                                i32.const 8
                                i32.shl
                                local.get 5
                                i32.const 24
                                i32.shr_u
                                i32.or
                                i32.store
                                local.get 8
                                i32.const 12
                                i32.add
                                local.get 2
                                i32.load
                                local.tee 5
                                i32.const 8
                                i32.shl
                                local.get 4
                                i32.const 24
                                i32.shr_u
                                i32.or
                                i32.store
                                local.get 8
                                i32.const 16
                                i32.add
                                local.set 8
                                local.get 2
                                i32.const 16
                                i32.add
                                local.set 2
                                local.get 7
                                i32.const -16
                                i32.add
                                local.tee 7
                                i32.const 16
                                i32.gt_u
                                br_if 0 (;@14;)
                              end
                              local.get 6
                              local.get 9
                              i32.sub
                              local.set 4
                              local.get 3
                              local.get 10
                              i32.add
                              local.set 3
                            end
                            i32.const 16
                            local.set 2
                            local.get 4
                            i32.const 16
                            i32.and
                            br_if 2 (;@10;)
                            br 3 (;@9;)
                          end
                          local.get 3
                          local.get 1
                          i32.load
                          local.tee 5
                          i32.store8
                          local.get 1
                          i32.const 16
                          i32.add
                          local.set 2
                          local.get 4
                          i32.const -17
                          i32.add
                          local.set 6
                          local.get 4
                          i32.const -1
                          i32.add
                          local.set 7
                          local.get 3
                          i32.const 1
                          i32.add
                          local.set 8
                          local.get 1
                          local.get 4
                          i32.const -20
                          i32.add
                          i32.const -16
                          i32.and
                          local.tee 9
                          i32.const 17
                          i32.add
                          local.tee 10
                          i32.add
                          local.set 1
                          loop  ;; label = @12
                            local.get 8
                            local.get 2
                            i32.const -12
                            i32.add
                            i32.load
                            local.tee 4
                            i32.const 24
                            i32.shl
                            local.get 5
                            i32.const 8
                            i32.shr_u
                            i32.or
                            i32.store
                            local.get 8
                            i32.const 4
                            i32.add
                            local.get 2
                            i32.const -8
                            i32.add
                            i32.load
                            local.tee 5
                            i32.const 24
                            i32.shl
                            local.get 4
                            i32.const 8
                            i32.shr_u
                            i32.or
                            i32.store
                            local.get 8
                            i32.const 8
                            i32.add
                            local.get 2
                            i32.const -4
                            i32.add
                            i32.load
                            local.tee 4
                            i32.const 24
                            i32.shl
                            local.get 5
                            i32.const 8
                            i32.shr_u
                            i32.or
                            i32.store
                            local.get 8
                            i32.const 12
                            i32.add
                            local.get 2
                            i32.load
                            local.tee 5
                            i32.const 24
                            i32.shl
                            local.get 4
                            i32.const 8
                            i32.shr_u
                            i32.or
                            i32.store
                            local.get 8
                            i32.const 16
                            i32.add
                            local.set 8
                            local.get 2
                            i32.const 16
                            i32.add
                            local.set 2
                            local.get 7
                            i32.const -16
                            i32.add
                            local.tee 7
                            i32.const 18
                            i32.gt_u
                            br_if 0 (;@12;)
                          end
                          local.get 3
                          local.get 10
                          i32.add
                          local.set 3
                          i32.const 16
                          local.set 2
                          local.get 6
                          local.get 9
                          i32.sub
                          local.tee 4
                          i32.const 16
                          i32.and
                          i32.eqz
                          br_if 2 (;@9;)
                          br 1 (;@10;)
                        end
                        local.get 3
                        local.get 1
                        i32.load
                        local.tee 5
                        i32.store8
                        local.get 3
                        local.get 1
                        i32.load8_u offset=1
                        i32.store8 offset=1
                        local.get 1
                        i32.const 16
                        i32.add
                        local.set 2
                        local.get 4
                        i32.const -18
                        i32.add
                        local.set 6
                        local.get 4
                        i32.const -2
                        i32.add
                        local.set 7
                        local.get 3
                        i32.const 2
                        i32.add
                        local.set 8
                        local.get 1
                        local.get 4
                        i32.const -20
                        i32.add
                        i32.const -16
                        i32.and
                        local.tee 9
                        i32.const 18
                        i32.add
                        local.tee 10
                        i32.add
                        local.set 1
                        loop  ;; label = @11
                          local.get 8
                          local.get 2
                          i32.const -12
                          i32.add
                          i32.load
                          local.tee 4
                          i32.const 16
                          i32.shl
                          local.get 5
                          i32.const 16
                          i32.shr_u
                          i32.or
                          i32.store
                          local.get 8
                          i32.const 4
                          i32.add
                          local.get 2
                          i32.const -8
                          i32.add
                          i32.load
                          local.tee 5
                          i32.const 16
                          i32.shl
                          local.get 4
                          i32.const 16
                          i32.shr_u
                          i32.or
                          i32.store
                          local.get 8
                          i32.const 8
                          i32.add
                          local.get 2
                          i32.const -4
                          i32.add
                          i32.load
                          local.tee 4
                          i32.const 16
                          i32.shl
                          local.get 5
                          i32.const 16
                          i32.shr_u
                          i32.or
                          i32.store
                          local.get 8
                          i32.const 12
                          i32.add
                          local.get 2
                          i32.load
                          local.tee 5
                          i32.const 16
                          i32.shl
                          local.get 4
                          i32.const 16
                          i32.shr_u
                          i32.or
                          i32.store
                          local.get 8
                          i32.const 16
                          i32.add
                          local.set 8
                          local.get 2
                          i32.const 16
                          i32.add
                          local.set 2
                          local.get 7
                          i32.const -16
                          i32.add
                          local.tee 7
                          i32.const 17
                          i32.gt_u
                          br_if 0 (;@11;)
                        end
                        local.get 3
                        local.get 10
                        i32.add
                        local.set 3
                        i32.const 16
                        local.set 2
                        local.get 6
                        local.get 9
                        i32.sub
                        local.tee 4
                        i32.const 16
                        i32.and
                        i32.eqz
                        br_if 1 (;@9;)
                      end
                      local.get 3
                      local.get 1
                      i32.load8_u offset=1
                      i32.store8 offset=1
                      local.get 3
                      local.get 1
                      i32.load8_u offset=2
                      i32.store8 offset=2
                      local.get 3
                      local.get 1
                      i32.load8_u offset=3
                      i32.store8 offset=3
                      local.get 3
                      local.get 1
                      i32.load8_u offset=4
                      i32.store8 offset=4
                      local.get 3
                      local.get 1
                      i32.load8_u offset=5
                      i32.store8 offset=5
                      local.get 3
                      local.get 1
                      i32.load8_u offset=6
                      i32.store8 offset=6
                      local.get 3
                      local.get 1
                      i32.load8_u offset=7
                      i32.store8 offset=7
                      local.get 3
                      local.get 1
                      i32.load8_u offset=8
                      i32.store8 offset=8
                      local.get 3
                      local.get 1
                      i32.load8_u offset=9
                      i32.store8 offset=9
                      local.get 3
                      local.get 1
                      i32.load8_u offset=10
                      i32.store8 offset=10
                      local.get 3
                      local.get 1
                      i32.load8_u offset=11
                      i32.store8 offset=11
                      local.get 3
                      local.get 1
                      i32.load8_u offset=12
                      i32.store8 offset=12
                      local.get 3
                      local.get 1
                      i32.load8_u offset=13
                      i32.store8 offset=13
                      local.get 3
                      local.get 1
                      i32.load8_u offset=14
                      i32.store8 offset=14
                      local.get 3
                      local.get 1
                      i32.load8_u
                      i32.store8
                      local.get 3
                      local.get 1
                      i32.load8_u offset=15
                      i32.store8 offset=15
                      local.get 3
                      local.get 2
                      i32.add
                      local.set 3
                      local.get 1
                      local.get 2
                      i32.add
                      local.set 1
                      i32.const 8
                      local.set 2
                      local.get 4
                      i32.const 8
                      i32.and
                      i32.eqz
                      br_if 1 (;@8;)
                      br 2 (;@7;)
                    end
                    i32.const 8
                    local.set 2
                    local.get 4
                    i32.const 8
                    i32.and
                    br_if 1 (;@7;)
                  end
                  i32.const 4
                  local.set 2
                  local.get 4
                  i32.const 4
                  i32.and
                  br_if 1 (;@6;)
                  br 2 (;@5;)
                end
                local.get 3
                local.get 1
                i32.load8_u
                i32.store8
                local.get 3
                local.get 1
                i32.load8_u offset=1
                i32.store8 offset=1
                local.get 3
                local.get 1
                i32.load8_u offset=2
                i32.store8 offset=2
                local.get 3
                local.get 1
                i32.load8_u offset=3
                i32.store8 offset=3
                local.get 3
                local.get 1
                i32.load8_u offset=4
                i32.store8 offset=4
                local.get 3
                local.get 1
                i32.load8_u offset=5
                i32.store8 offset=5
                local.get 3
                local.get 1
                i32.load8_u offset=6
                i32.store8 offset=6
                local.get 3
                local.get 1
                i32.load8_u offset=7
                i32.store8 offset=7
                local.get 3
                local.get 2
                i32.add
                local.set 3
                local.get 1
                local.get 2
                i32.add
                local.set 1
                i32.const 4
                local.set 2
                local.get 4
                i32.const 4
                i32.and
                i32.eqz
                br_if 1 (;@5;)
              end
              local.get 3
              local.get 1
              i32.load8_u
              i32.store8
              local.get 3
              local.get 1
              i32.load8_u offset=1
              i32.store8 offset=1
              local.get 3
              local.get 1
              i32.load8_u offset=2
              i32.store8 offset=2
              local.get 3
              local.get 1
              i32.load8_u offset=3
              i32.store8 offset=3
              local.get 3
              local.get 2
              i32.add
              local.set 3
              local.get 1
              local.get 2
              i32.add
              local.set 1
              i32.const 2
              local.set 2
              local.get 4
              i32.const 2
              i32.and
              i32.eqz
              br_if 1 (;@4;)
              br 2 (;@3;)
            end
            i32.const 2
            local.set 2
            local.get 4
            i32.const 2
            i32.and
            br_if 1 (;@3;)
          end
          local.get 4
          i32.const 1
          i32.and
          br_if 1 (;@2;)
          br 2 (;@1;)
        end
        local.get 3
        local.get 1
        i32.load8_u
        i32.store8
        local.get 3
        local.get 1
        i32.load8_u offset=1
        i32.store8 offset=1
        local.get 3
        local.get 2
        i32.add
        local.set 3
        local.get 1
        local.get 2
        i32.add
        local.set 1
        local.get 4
        i32.const 1
        i32.and
        i32.eqz
        br_if 1 (;@1;)
      end
      local.get 3
      local.get 1
      i32.load8_u
      i32.store8
    end
    local.get 0)
  (func $strlen (type 2) (param i32) (result i32)
    (local i32 i32 i32)
    local.get 0
    local.set 1
    block  ;; label = @1
      block  ;; label = @2
        block  ;; label = @3
          local.get 0
          i32.const 3
          i32.and
          i32.eqz
          br_if 0 (;@3;)
          local.get 0
          i32.load8_u
          i32.eqz
          br_if 1 (;@2;)
          local.get 0
          i32.const 1
          i32.add
          local.set 1
          loop  ;; label = @4
            local.get 1
            i32.const 3
            i32.and
            i32.eqz
            br_if 1 (;@3;)
            local.get 1
            i32.load8_u
            local.set 2
            local.get 1
            i32.const 1
            i32.add
            local.tee 3
            local.set 1
            local.get 2
            br_if 0 (;@4;)
          end
          local.get 3
          i32.const -1
          i32.add
          local.get 0
          i32.sub
          return
        end
        local.get 1
        i32.const -4
        i32.add
        local.set 1
        loop  ;; label = @3
          local.get 1
          i32.const 4
          i32.add
          local.tee 1
          i32.load
          local.tee 2
          i32.const -1
          i32.xor
          local.get 2
          i32.const -16843009
          i32.add
          i32.and
          i32.const -2139062144
          i32.and
          i32.eqz
          br_if 0 (;@3;)
        end
        local.get 2
        i32.const 255
        i32.and
        i32.eqz
        br_if 1 (;@1;)
        loop  ;; label = @3
          local.get 1
          i32.load8_u offset=1
          local.set 2
          local.get 1
          i32.const 1
          i32.add
          local.tee 3
          local.set 1
          local.get 2
          br_if 0 (;@3;)
        end
        local.get 3
        local.get 0
        i32.sub
        return
      end
      local.get 0
      local.get 0
      i32.sub
      return
    end
    local.get 1
    local.get 0
    i32.sub)
  (func $__wait (type 10) (param i32 i32 i32 i32)
    (local i32 i32)
    block  ;; label = @1
      block  ;; label = @2
        block  ;; label = @3
          block  ;; label = @4
            block  ;; label = @5
              block  ;; label = @6
                block  ;; label = @7
                  local.get 1
                  i32.eqz
                  br_if 0 (;@7;)
                  i32.const -100
                  local.set 4
                  loop  ;; label = @8
                    local.get 1
                    i32.load
                    br_if 3 (;@5;)
                    local.get 0
                    i32.load
                    local.get 2
                    i32.ne
                    br_if 7 (;@1;)
                    i32.const 375
                    call $__syscall0
                    call $__syscall_ret
                    drop
                    local.get 4
                    i32.const 1
                    i32.add
                    local.tee 4
                    br_if 0 (;@8;)
                    br 2 (;@6;)
                  end
                end
                i32.const -100
                local.set 4
                loop  ;; label = @7
                  local.get 0
                  i32.load
                  local.get 2
                  i32.ne
                  br_if 6 (;@1;)
                  i32.const 375
                  call $__syscall0
                  call $__syscall_ret
                  drop
                  local.get 4
                  i32.const 1
                  i32.add
                  local.tee 4
                  br_if 0 (;@7;)
                end
              end
              local.get 1
              i32.eqz
              br_if 1 (;@4;)
            end
            loop  ;; label = @5
              local.get 1
              i32.load
              local.tee 4
              local.get 1
              i32.load
              i32.ne
              br_if 0 (;@5;)
            end
            i32.const 1
            local.set 5
            local.get 1
            local.get 4
            i32.const 1
            i32.add
            i32.store
            local.get 0
            i32.load
            local.get 2
            i32.eq
            br_if 1 (;@3;)
            br 2 (;@2;)
          end
          i32.const 0
          local.set 5
          local.get 0
          i32.load
          local.get 2
          i32.ne
          br_if 1 (;@2;)
        end
        i32.const 128
        i32.const 0
        local.get 3
        select
        local.set 4
        loop  ;; label = @3
          block  ;; label = @4
            i32.const 240
            local.get 0
            local.get 4
            local.get 2
            i32.const 0
            call $__syscall4
            i32.const -38
            i32.ne
            br_if 0 (;@4;)
            i32.const 240
            local.get 0
            i32.const 0
            local.get 2
            i32.const 0
            call $__syscall4
            drop
          end
          local.get 0
          i32.load
          local.get 2
          i32.eq
          br_if 0 (;@3;)
        end
      end
      local.get 5
      i32.eqz
      br_if 0 (;@1;)
      loop  ;; label = @2
        local.get 1
        i32.load
        local.tee 2
        local.get 1
        i32.load
        i32.ne
        br_if 0 (;@2;)
      end
      local.get 1
      local.get 2
      i32.const -1
      i32.add
      i32.store
    end)
  (table (;0;) 5 5 funcref)
  (memory (;0;) 2)
  (global (;0;) (mut i32) (i32.const 67776))
  (global (;1;) i32 (i32.const 67776))
  (global (;2;) i32 (i32.const 2232))
  (export "memory" (memory 0))
  (export "__heap_base" (global 1))
  (export "__data_end" (global 2))
  (export "main" (func $main))
  (export "writev_c" (func $writev_c))
  (elem (;0;) (i32.const 1) $__stdio_write $__stdio_close $__stdout_write $__stdio_seek)
  (data (;0;) (i32.const 1024) "Hello World\00")
  (data (;1;) (i32.const 1040) "\05\00\00\00\00\00\00\00\00\00\00\00\02\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\03\00\00\00\04\00\00\00\b8\04\00\00\00\04\00\00\00\00\00\00\00\00\00\00\01\00\00\00\00\00\00\00\00\00\00\00\00\00\00\0a\ff\ff\ff\ff\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00")
  (data (;2;) (i32.const 1184) "\10\04\00\00")
  (data (;3;) (i32.const 1200) "\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00"))
