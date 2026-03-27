import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideEchartsCore } from 'ngx-echarts';
import * as echarts from 'echarts/core';
import { GraphChart, BarChart, LineChart, PieChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, LegendComponent, ToolboxComponent, GridComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { routes } from './app.routes';
import { jwtInterceptor } from './core/interceptors/jwt.interceptor';

echarts.use([GraphChart, BarChart, LineChart, PieChart, TitleComponent, TooltipComponent, LegendComponent, ToolboxComponent, GridComponent, CanvasRenderer]);

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(withInterceptors([jwtInterceptor])),
    provideAnimationsAsync(),
    provideEchartsCore({ echarts }),
  ],
};
