# Future Ideas

This document captures ideas that are intentionally out of current scope but worth revisiting.

## SharePoint-Linked SOP/Method Library for PWA (Offline Capable)

### Concept
- Add SOP and method links for each device in the PWA data model.
- Let users open the documents directly from each device row/detail view.
- Support offline use by downloading and caching selected docs on-device.

### Why It Could Help
- Gives field teams one place to find relevant methods and SOPs.
- Reduces time spent searching for current guidance in the field.
- Keeps SharePoint as the source of truth for document updates.

### Potential Approach
- Extend `air_monitoring_table.json` with per-device document metadata (title, type, URL, version/date).
- Add document UI in `table.html` (and/or detail modal) with "available offline" indicators.
- Expand service worker strategy in `sw.js` to cache selected document files for offline access.
- Use a sync process that mirrors approved SharePoint files into web-accessible app paths before deployment.

### Key Considerations
- SharePoint auth and CORS can block direct browser fetches depending on tenant settings.
- Browser storage limits require cache-size controls and selective/offline-on-demand downloads.
- Versioning/invalidation logic is needed to replace outdated SOPs cleanly.
- Large PDFs may impact initial sync/download performance.
