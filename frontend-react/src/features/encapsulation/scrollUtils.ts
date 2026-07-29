export const isNearBottom = (
  element: Pick<HTMLElement, 'scrollHeight' | 'scrollTop' | 'clientHeight'>,
  threshold = 2,
) => element.scrollHeight - element.scrollTop - element.clientHeight <= threshold;
