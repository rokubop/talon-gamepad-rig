tag: user.gamepad_rig_test
-

gamepad(left_xy):    user.gamepad_rig_test_record("stick", "left", x, y*-1)
gamepad(right_xy):   user.gamepad_rig_test_record("stick", "right", x, y*-1)
gamepad(l2:change):  user.gamepad_rig_test_record("trigger", "l2", value, 0)
gamepad(r2:change):  user.gamepad_rig_test_record("trigger", "r2", value, 0)
