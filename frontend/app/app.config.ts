export default defineAppConfig({
  ui: {
    colors: {
      primary: 'indigo',
      neutral: 'zinc'
    },
    card: {
      slots: {
        root: 'rounded-xl border border-muted bg-elevated/70 backdrop-blur-sm shadow-xs transition-all duration-200',
        header: 'p-4 sm:px-5 border-b border-muted',
        body: 'p-4 sm:p-5',
        footer: 'p-4 sm:px-5 border-t border-muted bg-muted/20'
      }
    },
    button: {
      defaultVariants: {
        size: 'sm'
      }
    }
  }
})
