export const seo = ({
  title,
  description,
}: {
  title: string
  description: string
}) => {
  const metaTags = [
    { name: 'description', content: description },
    { name: 'og:title', content: title },
    { name: 'og:description', content: description },
    { name: 'twitter:card', content: 'summary_large_image' },
    { name: 'twitter:title', content: title },
    { name: 'twitter:description', content: description },
  ]

  return metaTags
}
