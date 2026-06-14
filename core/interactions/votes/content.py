'''
Text templates for the Bluesky theme-vote post and its per-option comments.

The wording lives here in one place; the DTOs format these and hand finished
strings to callers (e.g. the posting notebook) via ``ThemeVote.post_text`` and
``ThemeOption.comment_text``. Edit the copy here without touching the DTOs.
'''

# the main poll post. ``{themes}`` is filled with the ballot's theme names, one
# per line.
POST_TEXT = (
    'THEME VOTE\n'
    '\n'
    "This week's themes:\n"
    '{themes}\n'
    '\n'
    'Vote for a theme by liking the corresponding reply.\n'
    'Voting is open for 24 hours after this post is published. '
    'The winning theme will be active for 2 days after the voting period concludes.'
)

# one reply per ballot option; liking it is a vote. ``{theme_name}`` is the
# option's display name, ``{theme_source}`` where it draws from and
# ``{theme_desc}`` its description.
COMMENT_TEXT = (
    'Like this reply to vote for: {theme_name}{theme_source}'
)
