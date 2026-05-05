import { renderHook, act } from '@testing-library/react';
import { useThresholdScroll } from './thresholdScroll';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('useThresholdScroll', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('should initialize with activeScreen 0', () => {
    const { result } = renderHook(() => useThresholdScroll({ sectionCount: 4 }));
    expect(result.current.activeScreen).toBe(0);
  });

  it('should navigate to next screen programmatically', () => {
    const { result } = renderHook(() => useThresholdScroll({ sectionCount: 4 }));
    
    act(() => {
      result.current.navigateTo(1);
    });

    expect(result.current.activeScreen).toBe(1);
  });

  it('should ignore navigation if already animating', () => {
    const { result } = renderHook(() => useThresholdScroll({ sectionCount: 4, animationDuration: 600 }));
    
    act(() => {
      result.current.navigateTo(1);
    });
    
    // Immediately try to navigate again
    act(() => {
      result.current.navigateTo(2);
    });

    // Should still be 1 because animation is in progress
    expect(result.current.activeScreen).toBe(1);

    // Fast forward time
    act(() => {
      vi.advanceTimersByTime(650);
    });

    // Now it should be possible
    act(() => {
      result.current.navigateTo(2);
    });
    expect(result.current.activeScreen).toBe(2);
  });

  it('should handle significant scroll down event (wheel)', () => {
    const { result } = renderHook(() => useThresholdScroll({ sectionCount: 4 }));
    
    act(() => {
      const event = new WheelEvent('wheel', { deltaY: 100 });
      window.dispatchEvent(event);
    });

    expect(result.current.activeScreen).toBe(1);
  });

  it('should handle significant scroll up event (wheel)', () => {
    const { result } = renderHook(() => useThresholdScroll({ sectionCount: 4 }));
    
    // First go to page 1
    act(() => {
      result.current.navigateTo(1);
      vi.advanceTimersByTime(1000);
    });

    // Scroll up
    act(() => {
      const event = new WheelEvent('wheel', { deltaY: -100 });
      window.dispatchEvent(event);
    });

    expect(result.current.activeScreen).toBe(0);
  });

  it('should handle touch swipe exceeding threshold', () => {
    const { result } = renderHook(() => useThresholdScroll({ sectionCount: 4, thresholdDistance: 60 }));
    
    // Simulate Touch Start
    act(() => {
      const touchStart = new TouchEvent('touchstart', {
        touches: [{ clientY: 500 } as Touch]
      });
      window.dispatchEvent(touchStart);
    });

    // Simulate Touch End (Swipe Up / Scroll Down) -> clientY decreases
    // Distance = 500 - 400 = 100px (> 60px)
    act(() => {
      const touchEnd = new TouchEvent('touchend', {
        changedTouches: [{ clientY: 400 } as Touch]
      });
      window.dispatchEvent(touchEnd);
    });

    expect(result.current.activeScreen).toBe(1);
  });

  it('should not navigate if touch swipe is below threshold', () => {
    const { result } = renderHook(() => useThresholdScroll({ sectionCount: 4, thresholdDistance: 60 }));
    
    // Distance = 500 - 450 = 50px (< 60px)
    // Velocity needs to be low. Duration needs to be high.
    // Let's say duration is 1000ms. Velocity = 50/1000 = 0.05 px/ms (< 1.2)
    
    // Simulate Touch Start at t=0
    act(() => {
      vi.setSystemTime(0);
      const touchStart = new TouchEvent('touchstart', {
        touches: [{ clientY: 500 } as Touch]
      });
      window.dispatchEvent(touchStart);
    });

    // Simulate Touch End at t=1000
    act(() => {
      vi.setSystemTime(1000);
      const touchEnd = new TouchEvent('touchend', {
        changedTouches: [{ clientY: 450 } as Touch]
      });
      window.dispatchEvent(touchEnd);
    });

    expect(result.current.activeScreen).toBe(0);
  });
});
