# Document parsing security limitations

This Demo is intended only for controlled, anonymized sample resumes. Do not expose its document
upload path to public or otherwise untrusted traffic in its current form.

The parser applies file-size, text-length, image-pixel, DOCX ZIP, PDF page, PDF object-depth, and
decoded-content budgets. These checks are defense in depth; they are not a sandbox. In particular,
`pypdf` must materialize an individual decoded PDF stream before the application can measure and
reject its decoded size. Crafted parser inputs may therefore consume substantial memory or CPU
before an application-level limit is observed.

Before accepting untrusted uploads, run document parsing in a dedicated subprocess or isolated
worker with enforced memory and wall-clock limits. Keep the existing DOCX and PDF budgets inside
that worker, and treat parser crashes, timeouts, and resource-limit exits as rejected documents.

The project README should link to this document when the final Demo documentation is assembled.
