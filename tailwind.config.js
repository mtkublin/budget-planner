/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/budget_planner/web/templates/**/*.html',
    './src/budget_planner/web/static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        surface: 'var(--surface)',
        'surface-raised': 'var(--surface-raised)',
        'surface-sunken': 'var(--surface-sunken)',
        ink: 'var(--ink)',
        muted: 'var(--muted)',
        faint: 'var(--faint)',
        rule: 'var(--rule)',
        'rule-strong': 'var(--rule-strong)',
        accent: 'var(--accent)',
        'accent-ink': 'var(--accent-ink)',
        'accent-wash': 'var(--accent-wash)',
      },
    },
  },
  plugins: [],
};
