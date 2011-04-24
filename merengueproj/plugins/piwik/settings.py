# Copyright (c) 2010 by Yaco Sistemas <dgarcia@yaco.es>
#
# This file is part of Merengue.
#
# Merengue is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Merengue is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Merengue.  If not, see <http://www.gnu.org/licenses/>.

# default date range and metric to get piwik stats
PERIOD = 'year'
DATE = 'today'
METRIC = 'sum_daily_nb_uniq_visitors'

# You can trace stats by custom variables instead page titles.
#IMPORTANT: if you change it to True,you must change
# the visit_standard_length to 0 in /var/www/piwik/config/global.ini.php so piwik
# traces fine. This change means losing some statistics as average time on a page
CUSTOM_VARIABLES = False
