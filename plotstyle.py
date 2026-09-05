################################################################################
# Site-local plotting shim. Import this instead of plottools from a blog post:  #
#                                                                              #
#     import plotstyle as pt                                                    #
#                                                                              #
# It re-exports the whole plottools API and selects the 'blog_post' style, so   #
# pt.add_subplots(), pt.plot_1d_func() and friends pick up the site's figure    #
# geometry without a style= argument at every call site.                        #
#                                                                              #
# This file deliberately holds no plotting code of its own. plottools lives in  #
# the lqcd repository and stays the single copy; what belongs here is only the  #
# choice of style, which is a fact about the website rather than about lqcd.    #
#                                                                              #
# The style must be selected *after* plottools is imported and by mutating      #
# default_style in place -- see formattools.set_default_style for why.          #
#                                                                              #
# Author: Patrick Oare                                                          #
################################################################################

from plottools import *

set_default_style('blog_post')
