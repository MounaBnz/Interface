import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { ToastrService } from 'ngx-toastr';
import { Observable } from 'rxjs';
import { API_URL } from 'src/app/env';


interface EmbryoImageResult {
  image_path:string;
  image_name: string;
  result: string;
  suggested_value: string;
  note: string;
}

interface EmbryoFormData {
  image_name: string;
  result: string;
  suggested_value: string;
  note: string;
}
@Injectable({
  providedIn: 'root'
})
export class EmbryonService {

  constructor(private http:HttpClient, private toastr: ToastrService) { }
  getEmbryoImagesAndResults(): Observable<EmbryoImageResult[]> {
    return this.http.get<EmbryoImageResult[]>(`${API_URL}/images`)  ;
  }

  validateAndPostFormData(embryo: EmbryoImageResult, selectedValue: string, note: string): void {
    if (!selectedValue && !note?.trim()) {
      this.toastr.error('Please select a value from the dropdown or add a comment.', 'Validation Error');
      return;
    }

    const formData: EmbryoFormData = {
      image_name: embryo.image_name,
      result:embryo.result,
      suggested_value: selectedValue,
      note: note.trim()
    };
    console.log(formData)

    this.http.post(`${API_URL}/update`, formData);
    this.http.post<any>(`${API_URL}/update`, formData).subscribe(
      (response) => {
        this.toastr.success('Form data submitted successfully!', 'Success');
      },
      (error) => {
        this.toastr.error('Error submitting form data. Please try again later.', 'Submission Error');
        console.error('Error submitting form data', error);
      }
    );
  }


}
