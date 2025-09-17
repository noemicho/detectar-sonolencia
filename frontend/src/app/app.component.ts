import { HttpClient, HttpClientModule } from '@angular/common/http';
import { Component, ElementRef, ViewChild } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NgIf } from '@angular/common';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, HttpClientModule, NgIf],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {

  @ViewChild('video') videoRef!: ElementRef;
  @ViewChild('overlay') overlayRef!: ElementRef;
  data: any;
  showOverlay: boolean = false;
  showButton: boolean = false;

  constructor(private http: HttpClient) {}
  
  async startDetection() {
    await this.http.post('http://localhost:5000/reset', {}).toPromise();

    const video = this.videoRef.nativeElement;
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;

    setInterval(() => this.captureAndSend(video), 200); // 5 frames por segundo
  }

  captureAndSend(video: HTMLVideoElement) {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg');

    this.http.post('http://localhost:5000/process_frame', { image: dataUrl })
      .subscribe(res => {
        this.data = res;
        if (this.data) {
          this.showButton = true;
        }
        if(this.showOverlay){
          this.drawOverlay(res);
        }
        else{
          const overlayCanvas: HTMLCanvasElement = this.overlayRef.nativeElement;
          const ctx = overlayCanvas.getContext('2d')!;
          ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
        }
      });
  }

  toggleOverlay(){
    this.showOverlay = !this.showOverlay;
  }

  drawOverlay(res: any) {
    const canvas: HTMLCanvasElement = this.overlayRef.nativeElement;
    const video: HTMLVideoElement = this.videoRef.nativeElement;
    const ctx = canvas.getContext('2d')!;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;


    ctx.clearRect(0, 0, canvas.width, canvas.height);
  
    // Olhos
    if (res.eyes) {
      ctx.strokeStyle = "blue";
      ctx.fillStyle = "cyan";
      ctx.lineWidth = 2;
  
      ctx.beginPath();
      const scaleX = canvas.width / res.frame_width;
      const scaleY = canvas.height / res.frame_height;

      res.eyes.forEach((pt: any, i: number) => {
        let x = pt.x * scaleX;
        let y = pt.y * scaleY;
        x = canvas.width - x;

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
  
        ctx.beginPath();
        ctx.arc(x, y, 2, 0, 2 * Math.PI);
        ctx.fill();
      });
      ctx.closePath();
      ctx.stroke();
    }
  
    // Boca
    if (res.mouth) {
      ctx.strokeStyle = "magenta";
      ctx.fillStyle = "pink";
      ctx.lineWidth = 2;
  
      ctx.beginPath();
      const scaleX = canvas.width / res.frame_width;
      const scaleY = canvas.height / res.frame_height;

      res.mouth.forEach((pt: any, i: number) => {
        let x = pt.x * scaleX;
        let y = pt.y * scaleY;
        x = canvas.width - x;

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
  
        ctx.beginPath();
        ctx.arc(x, y, 2, 0, 2 * Math.PI);
        ctx.fill();
      });
      ctx.closePath();
      ctx.stroke();
    }

    // Contorno do rosto
    if (res.face) {
      ctx.strokeStyle = "gray";
      ctx.fillStyle = "white";
      ctx.lineWidth = 2;
  
      ctx.beginPath();
      const scaleX = canvas.width / res.frame_width;
      const scaleY = canvas.height / res.frame_height;

      res.face.forEach((pt: any, i: number) => {
        let x = pt.x * scaleX;
        let y = pt.y * scaleY;
        x = canvas.width - x;

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
  
        ctx.beginPath();
        ctx.arc(x, y, 2, 0, 2 * Math.PI);
        ctx.fill();
      });
      ctx.closePath();
      ctx.stroke();
    }
  }
}
