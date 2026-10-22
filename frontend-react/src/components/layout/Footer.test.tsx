import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import Footer from './Footer';

describe('Footer', () => {
  it('shows the institution, platform, and contact link', () => {
    render(<Footer />);

    expect(screen.getByText('Zhejiang Gongshang University')).toBeTruthy();
    expect(screen.getByText('School of Food Science and Biotechnology')).toBeTruthy();
    expect(
      screen.getByText(
        'Copyright © 2026 SweetSeek Academic Research Platform. All Rights Reserved by FCN Lab.',
      ),
    ).toBeTruthy();
    expect(screen.getByRole('link', { name: 'hjxie@zjgsu.edu.cn' }).getAttribute('href')).toBe(
      'mailto:hjxie@zjgsu.edu.cn',
    );
    expect(screen.getByRole('link', { name: '豫ICP备2026004112号-1' }).getAttribute('href')).toBe(
      'https://beian.miit.gov.cn/',
    );
  });
});
