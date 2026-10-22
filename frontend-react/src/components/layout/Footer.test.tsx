import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import Footer from './Footer';

describe('Footer', () => {
  it('shows the institution, platform, and contact link', () => {
    render(<Footer />);

    expect(screen.getByText('Zhejiang Gongshang University')).toBeTruthy();
    expect(screen.getByText('School of Food Science and Biotechnology')).toBeTruthy();
    expect(screen.getByText('SweetSeek Academic Research Platform')).toBeTruthy();
    expect(screen.getByText('Copyright © 2026 FCN Lab. All Rights Reserved.')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Contact Us' }).getAttribute('href')).toBe(
      'mailto:hjxie@zjgsu.edu.cn',
    );
    expect(screen.getByRole('link', { name: '豫ICP备2026004112号-1' }).getAttribute('href')).toBe(
      'https://beian.miit.gov.cn/',
    );
  });

  it('can participate in normal page flow', () => {
    const footer = render(<Footer placement="flow" />);

    expect(footer.container.firstElementChild?.classList.contains('sweetseek-footer--flow')).toBe(true);
  });

  it('supports a muted page-matching background', () => {
    const footer = render(<Footer tone="muted" />);

    expect(footer.container.firstElementChild?.classList.contains('sweetseek-footer--muted')).toBe(true);
  });
});
