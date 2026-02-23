"""Simple test/example for gamepad rig

Run this manually to test basic functionality.
"""

from talon import actions, cron
import time


def test_basic_stick():
    """Test basic stick movement"""
    print("Testing basic stick movement...")
    gamepad = actions.user.gamepad_rig()
    
    # Move stick to right
    print("  Moving left stick to right (1, 0)")
    gamepad.left_thumb.to(1, 0)
    
    # Wait a bit
    time.sleep(1)
    
    # Center stick
    print("  Centering stick")
    gamepad.left_thumb.to(0, 0)
    
    print("✓ Basic stick test complete")


def test_smooth_transition():
    """Test smooth stick transition"""
    print("\nTesting smooth transition...")
    gamepad = actions.user.gamepad_rig()
    
    # Smooth movement over 1 second
    print("  Moving left stick to right over 1 second")
    gamepad.left_thumb.to(1, 0).over(1000)
    
    # Wait for completion
    time.sleep(1.5)
    
    # Smooth return to center
    print("  Returning to center over 500ms")
    gamepad.left_thumb.to(0, 0).over(500)
    
    time.sleep(1)
    print("✓ Smooth transition test complete")


def test_trigger():
    """Test trigger control"""
    print("\nTesting trigger control...")
    gamepad = actions.user.gamepad_rig()
    
    # Press trigger
    print("  Pressing left trigger")
    gamepad.left_trigger.to(1)
    
    time.sleep(0.5)
    
    # Release trigger
    print("  Releasing trigger")
    gamepad.left_trigger.to(0)
    
    print("✓ Trigger test complete")


def test_stop():
    """Test stop functionality"""
    print("\nTesting stop...")
    gamepad = actions.user.gamepad_rig()
    
    # Set some values
    print("  Setting stick and trigger values")
    gamepad.left_thumb.to(1, 0)
    gamepad.left_trigger.to(0.5)
    
    time.sleep(0.5)
    
    # Stop everything
    print("  Stopping all")
    gamepad.stop()
    
    print("✓ Stop test complete")


def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("Gamepad Rig - Basic Tests")
    print("="*60)
    
    try:
        test_basic_stick()
        test_smooth_transition()
        test_trigger()
        test_stop()
        
        print("\n" + "="*60)
        print("All tests complete!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


# To run tests, call from Talon REPL:
# from user.roku.mouse_rig.gamepad import example_usage
# example_usage.run_all_tests()
