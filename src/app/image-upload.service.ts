import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ImageUploadService {

  private apiUrl = 'http://localhost:5000/analyse-embryon';

  constructor(private http: HttpClient) { }

  uploadImage(image: File): Observable<any> {
    const formData: FormData = new FormData();
    formData.append('file', image, image.name);
    return this.http.post<any>(this.apiUrl, formData);
  }
}
