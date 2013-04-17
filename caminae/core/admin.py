from django.contrib import admin

from caminae.authent.admin import PathManagerModelAdmin
from caminae.core.models import (Datasource, Stake, Usage, Network, Trail,
                                 Comfort,)


admin.site.register(Datasource, PathManagerModelAdmin)
admin.site.register(Stake, PathManagerModelAdmin)
admin.site.register(Usage, PathManagerModelAdmin)
admin.site.register(Network, PathManagerModelAdmin)
admin.site.register(Trail, PathManagerModelAdmin)
admin.site.register(Comfort, PathManagerModelAdmin)
