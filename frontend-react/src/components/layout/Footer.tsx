interface FooterProps {
  placement?: 'anchored' | 'flow';
  tone?: 'default' | 'muted';
}

const Footer = ({ placement = 'anchored', tone = 'default' }: FooterProps) => (
  <footer
    className={`sweetseek-footer sweetseek-footer--${placement} sweetseek-footer--${tone}`}
    aria-label="Institution, contact, and filing information"
  >
    <div className="sweetseek-footer__content">
      <nav className="sweetseek-footer__links" aria-label="Footer links">
        <a href="https://www.zjgsu.edu.cn/" target="_blank" rel="noopener noreferrer">
          Zhejiang Gongshang University
        </a>
        <span className="sweetseek-footer__separator" aria-hidden="true" />
        <span>School of Food Science and Biotechnology</span>
        <span className="sweetseek-footer__separator" aria-hidden="true" />
        <a href="https://www.x-mol.com/groups/hujun_xie" target="_blank" rel="noopener noreferrer">
          FCN Lab
        </a>
        <span className="sweetseek-footer__separator" aria-hidden="true" />
        <a href="mailto:hjxie@zjgsu.edu.cn">Contact Us</a>
        <span className="sweetseek-footer__separator" aria-hidden="true" />
        <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">
          豫ICP备2026004112号-1
        </a>
      </nav>

      <div className="sweetseek-footer__legal">
        <span>SweetSeek Academic Research Platform</span>
        <span>Copyright © 2026 FCN Lab. All Rights Reserved.</span>
      </div>
    </div>

  </footer>
);

export default Footer;
