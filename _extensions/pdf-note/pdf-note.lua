-- Shared presentation markup for every notes stub page.
--
-- Each note page is otherwise identical: an accent rule, the front-matter
-- description repeated as body prose, a download button, and an inline PDF
-- viewer. Hand-copying that into 20-30 files meant the slug was typed four
-- times per note and changing the presentation was a 30-file edit. This
-- shortcode owns all of it; a stub's body is one line.
--
-- Usage:  {{< pdf-note >}}              slug derived from the filename
--         {{< pdf-note explicit-slug >}} slug given explicitly

-- notes/<topic>/<slug>.md -> "<slug>". Handles both path separators so the
-- extension is not silently macOS/Linux-only.
local function slug_from_input_file()
  local input = quarto.doc.input_file
  if input == nil then
    return nil
  end
  return tostring(input):match("([^/\\]+)%.[^.]+$")
end

return {
  ["pdf-note"] = function(args, kwargs, meta)
    local slug
    if #args > 0 then
      slug = pandoc.utils.stringify(args[1])
    else
      slug = slug_from_input_file()
    end

    -- Failing loudly matters more than usual here: a nil slug would
    -- otherwise produce "../pdf/nil.pdf" on a page that still looks
    -- plausible, and the broken download would only be found by clicking.
    if slug == nil or slug == "" then
      error(
        "pdf-note: could not determine the note slug from the input " ..
        "filename. Pass it explicitly: {{< pdf-note my-note-slug >}}"
      )
    end

    local pdf_path = "../pdf/" .. slug .. ".pdf"

    -- Reuse the description's inlines rather than flattening to a string,
    -- so markup in the front matter (maths, emphasis) survives.
    local description_inlines = pandoc.Inlines({})
    if meta ~= nil and meta.description ~= nil then
      if type(meta.description) == "table" then
        description_inlines = pandoc.Inlines(meta.description)
      else
        description_inlines = pandoc.Inlines(
          {pandoc.Str(pandoc.utils.stringify(meta.description))}
        )
      end
    end

    local accent_rule = pandoc.Div(
      pandoc.Blocks({}),
      pandoc.Attr("", {"accent-rule"}, {})
    )

    local download_button = pandoc.Para(pandoc.Inlines({
      pandoc.Link(
        pandoc.Inlines({pandoc.Str("Download"), pandoc.Space(), pandoc.Str("PDF")}),
        pdf_path,
        "",
        pandoc.Attr("", {"btn", "btn-primary"}, {})
      )
    }))

    local viewer = pandoc.RawBlock("html", table.concat({
      '<object data="' .. pdf_path .. '" type="application/pdf" ',
      'width="100%" height="800">\n',
      '  <p>Your browser cannot display PDFs inline.\n',
      '     <a href="' .. pdf_path .. '">Download it instead</a>.</p>\n',
      '</object>'
    }))

    return pandoc.Blocks({
      accent_rule,
      pandoc.Para(description_inlines),
      download_button,
      viewer,
    })
  end
}
