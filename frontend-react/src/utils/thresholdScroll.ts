import { useState, useEffect, useRef, useCallback } from 'react';

interface UseThresholdScrollOptions {
  thresholdDistance?: number; // px
  thresholdVelocity?: number; // px/ms
  animationDuration?: number; // ms
  sectionCount: number;
}

export const useThresholdScroll = ({
  thresholdDistance = 60,
  thresholdVelocity = 1.2,
  animationDuration = 600,
  sectionCount
}: UseThresholdScrollOptions) => {
  const [activeScreen, setActiveScreen] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const lastScrollTime = useRef(0);
  const touchStartY = useRef(0);
  const touchStartTime = useRef(0);

  const navigateTo = useCallback((index: number) => {
    if (index < 0 || index >= sectionCount) return;
    if (isAnimating) return;

    setIsAnimating(true);
    setActiveScreen(index);

    setTimeout(() => {
      setIsAnimating(false);
    }, animationDuration);
  }, [sectionCount, isAnimating, animationDuration]);

  // Wheel Handler
  const handleWheel = useCallback((e: WheelEvent) => {
    // 允许在非全屏滚动区域（如模态框内部）进行默认滚动
    // 通过检查事件目标的祖先元素是否有 .overflow-y-auto 或 .overflow-auto 类
    let target = e.target instanceof HTMLElement ? e.target : null;
    while (target && target !== document.body) {
        if (target.classList.contains('overflow-y-auto') || target.classList.contains('overflow-auto')) {
            // 如果该元素可以滚动（内容高度 > 视口高度），则不拦截
            if (target.scrollHeight > target.clientHeight) {
                // 这里我们要小心，如果是在这种可滚动元素内部滚动到底部或顶部，是否应该触发页面翻页？
                // 通常为了用户体验，我们应该阻止事件冒泡到页面级翻页逻辑
                return; 
            }
        }
        target = target.parentElement;
    }

    // 阻止默认滚动行为，接管为翻页
    e.preventDefault();
    
    // 如果正在动画中，则忽略
    if (isAnimating) return;

    const now = Date.now();
    // 增加冷却时间判断，防止连续触发
    if (now - lastScrollTime.current < 1000) return;

    // 优化触控板双指滑动检测
    // 触控板通常会产生带有小数的 deltaY，且惯性滑动会有衰减
    // 鼠标滚轮通常是固定的整数值（如 100）
    
    // 阈值设定：对于触控板，灵敏度需要较高；对于鼠标，防误触
    const isTouchpad = Math.abs(e.deltaY) < 100 && Math.abs(e.deltaY) > 0;
    const threshold = isTouchpad ? 5 : 20;

    if (Math.abs(e.deltaY) > threshold) {
        if (e.deltaY > 0) {
            // 向下滚动 -> 下一屏
            setActiveScreen(prev => {
                if (prev < sectionCount - 1) {
                    lastScrollTime.current = now;
                    // 设置动画状态，防止多次触发
                    setIsAnimating(true);
                    setTimeout(() => setIsAnimating(false), animationDuration);
                    return prev + 1;
                }
                return prev;
            });
        } else {
            // 向上滚动 -> 上一屏
            setActiveScreen(prev => {
                if (prev > 0) {
                    lastScrollTime.current = now;
                    // 设置动画状态，防止多次触发
                    setIsAnimating(true);
                    setTimeout(() => setIsAnimating(false), animationDuration);
                    return prev - 1;
                }
                return prev;
            });
        }
    }
  }, [sectionCount, isAnimating, animationDuration]);

  // Touch Handlers
  const handleTouchStart = useCallback((e: TouchEvent) => {
    touchStartY.current = e.touches[0].clientY;
    touchStartTime.current = Date.now();
  }, []);

  const handleTouchEnd = useCallback((e: TouchEvent) => {
    const touchEndY = e.changedTouches[0].clientY;
    const touchEndTime = Date.now();
    
    const distance = touchStartY.current - touchEndY; // Positive = Swipe Up (Scroll Down)
    const duration = touchEndTime - touchStartTime.current;
    const velocity = Math.abs(distance) / duration;

    // Check thresholds
    // Distance > 0 means Swipe Up (Scroll Down)
    // Distance < 0 means Swipe Down (Scroll Up)
    
    // Only navigate if threshold met
    if (Math.abs(distance) >= thresholdDistance || velocity >= thresholdVelocity) {
        if (distance > 0) {
            navigateTo(activeScreen + 1);
        } else {
            navigateTo(activeScreen - 1);
        }
    } else {
        // Bounce back (no navigation)
    }
    // Else: bounce back (handled by UI state not changing)
  }, [activeScreen, navigateTo, thresholdDistance, thresholdVelocity]);

  // Keyboard Handler
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // 允许在输入框中正常使用方向键
    const target = e.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        return;
    }

    if (e.key === 'ArrowDown' || e.key === 'PageDown') {
        e.preventDefault();
        navigateTo(activeScreen + 1);
    } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
        e.preventDefault();
        navigateTo(activeScreen - 1);
    }
  }, [activeScreen, navigateTo]);

  // Setup Global Listeners
  useEffect(() => {
    // 使用 { passive: false } 以便我们可以调用 e.preventDefault()
    window.addEventListener('wheel', handleWheel, { passive: false });
    window.addEventListener('touchstart', handleTouchStart, { passive: true });
    window.addEventListener('touchend', handleTouchEnd, { passive: true });
    window.addEventListener('keydown', handleKeyDown);
    
    return () => {
      window.removeEventListener('wheel', handleWheel);
      window.removeEventListener('touchstart', handleTouchStart);
      window.removeEventListener('touchend', handleTouchEnd);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleWheel, handleTouchStart, handleTouchEnd, handleKeyDown]);

  return { activeScreen, navigateTo };
};
