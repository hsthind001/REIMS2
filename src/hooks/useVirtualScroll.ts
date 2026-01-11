import { useState, useEffect, useRef, useMemo } from 'react';

export interface UseVirtualScrollOptions {
  itemHeight: number;
  containerHeight: number;
  overscan?: number;
  gap?: number;
}

export interface VirtualItem {
  index: number;
  offsetTop: number;
  height: number;
}

export function useVirtualScroll<T>(
  items: T[],
  options: UseVirtualScrollOptions
) {
  const { itemHeight, containerHeight, overscan = 3, gap = 0 } = options;
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleScroll = (event: Event) => {
    const target = event.target as HTMLDivElement;
    setScrollTop(target.scrollTop);
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  const virtualItems = useMemo(() => {
    const totalHeight = items.length * (itemHeight + gap);
    const startIndex = Math.max(0, Math.floor(scrollTop / (itemHeight + gap)) - overscan);
    const endIndex = Math.min(
      items.length - 1,
      Math.ceil((scrollTop + containerHeight) / (itemHeight + gap)) + overscan
    );

    const visibleItems: VirtualItem[] = [];
    for (let i = startIndex; i <= endIndex; i++) {
      visibleItems.push({
        index: i,
        offsetTop: i * (itemHeight + gap),
        height: itemHeight,
      });
    }

    return {
      virtualItems: visibleItems,
      totalHeight,
      startIndex,
      endIndex,
    };
  }, [items.length, scrollTop, itemHeight, containerHeight, overscan, gap]);

  return {
    containerRef,
    virtualItems: virtualItems.virtualItems,
    totalHeight: virtualItems.totalHeight,
    scrollToIndex: (index: number) => {
      if (containerRef.current) {
        containerRef.current.scrollTop = index * (itemHeight + gap);
      }
    },
  };
}

// Hook for variable height items (more complex)
export interface UseVariableVirtualScrollOptions {
  containerHeight: number;
  estimateItemHeight: (index: number) => number;
  overscan?: number;
}

export function useVariableVirtualScroll<T>(
  items: T[],
  options: UseVariableVirtualScrollOptions
) {
  const { containerHeight, estimateItemHeight, overscan = 3 } = options;
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const measurementsRef = useRef<Map<number, number>>(new Map());

  const handleScroll = (event: Event) => {
    const target = event.target as HTMLDivElement;
    setScrollTop(target.scrollTop);
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  const getItemOffset = (index: number) => {
    let offset = 0;
    for (let i = 0; i < index; i++) {
      offset += measurementsRef.current.get(i) || estimateItemHeight(i);
    }
    return offset;
  };

  const getTotalHeight = () => {
    let height = 0;
    for (let i = 0; i < items.length; i++) {
      height += measurementsRef.current.get(i) || estimateItemHeight(i);
    }
    return height;
  };

  const virtualItems = useMemo(() => {
    const visibleItems: VirtualItem[] = [];
    let currentOffset = 0;
    let startIndex = -1;

    for (let i = 0; i < items.length; i++) {
      const height = measurementsRef.current.get(i) || estimateItemHeight(i);

      if (currentOffset + height >= scrollTop - overscan * height && startIndex === -1) {
        startIndex = i;
      }

      if (startIndex !== -1 && currentOffset <= scrollTop + containerHeight + overscan * height) {
        visibleItems.push({
          index: i,
          offsetTop: currentOffset,
          height,
        });
      }

      if (currentOffset > scrollTop + containerHeight + overscan * height) {
        break;
      }

      currentOffset += height;
    }

    return visibleItems;
  }, [items.length, scrollTop, containerHeight, overscan, estimateItemHeight]);

  const measureItem = (index: number, height: number) => {
    measurementsRef.current.set(index, height);
  };

  return {
    containerRef,
    virtualItems,
    totalHeight: getTotalHeight(),
    measureItem,
    scrollToIndex: (index: number) => {
      if (containerRef.current) {
        containerRef.current.scrollTop = getItemOffset(index);
      }
    },
  };
}
