import React from 'react';

const sidebarStyles = {
  width: '256px',
  height: '100vh',
  position: 'fixed',
  top: 0,
  left: 0,
  backgroundColor: '#E3655B',
  color: 'white',
  padding: '1.25rem',
  borderTopRightRadius: '1rem',
  borderBottomRightRadius: '1rem',
  borderTopLeftRadius: '0',
  borderBottomLeftRadius: '0',
  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  zIndex: 1000,
  fontFamily: 'Poppins, Segoe UI, Arial, sans-serif',
};

const navLinkStyles = {
  display: 'block',
  marginBottom: '1rem',
  color: 'white',
  textDecoration: 'none',
  fontSize: '1.15rem',
  fontWeight: 500,
  letterSpacing: '0.03em',
  borderRadius: '0.5rem',
  padding: '0.5rem 1rem',
  transition: 'background 0.2s, color 0.2s',
};

const ulStyles = {
  listStyle: 'none',
  padding: 0,
  margin: 0,
};

const Sidebar = () => {
  // Custom hover effect using React state
  const [hovered, setHovered] = React.useState(null);
  const links = [
    { label: 'Home', href: '#' },
    { label: 'Profile', href: '#' },
    { label: 'Settings', href: '#' },
  ];
  return (
    <div style={sidebarStyles}>
      <h2 style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '2.5rem', letterSpacing: '0.05em', fontFamily: 'inherit' }}>Navigation</h2>
      <ul style={ulStyles}>
        {links.map((link, idx) => (
          <li key={link.label}>
            <a
              href={link.href}
              style={{
                ...navLinkStyles,
                background: hovered === idx ? 'rgba(255,255,255,0.15)' : 'none',
                color: hovered === idx ? '#FFF9F2' : 'white',
                boxShadow: hovered === idx ? '0 2px 8px rgba(0,0,0,0.08)' : 'none',
              }}
              onMouseEnter={() => setHovered(idx)}
              onMouseLeave={() => setHovered(null)}
            >
              {link.label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Sidebar;
