import { Component } from '@angular/core';
import { WelcomePage } from './features/welcome/welcome-page';

@Component({
  selector: 'app-root',
  imports: [WelcomePage],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {}
