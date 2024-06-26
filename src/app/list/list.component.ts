import { Component, OnInit } from '@angular/core';
import { EmbryonService } from '../services/embryon-service.service';
import { HttpClient } from '@angular/common/http';
import { ToastrService } from 'ngx-toastr';



interface EmbryoImageResult {
  image_path:string;
  image_name: string;
  result: string;
  suggested_value: string;
  note: string;
}
interface EmbryoFormData {
  image_path: string;
  value: string;
  note: string;
}
@Component({
  selector: 'app-list',
  templateUrl: './list.component.html',
  styleUrls: ['./list.component.css']
})
export class ListComponent implements OnInit {
  // analysisResults: any = null;
  analysisResults: EmbryoImageResult[] = [];
  error: string | null = null;
  notes: { [key: string]: string } = {};

  suggestedValues: string[] = ['poor', 'average', 'good'];
  selectedValues: { [key: string]: string } = {};

  constructor(private embryonService: EmbryonService, private http: HttpClient, private toastr: ToastrService) { }


  ngOnInit(): void {
    this.embryonService.getEmbryoImagesAndResults().subscribe(
      (data) => {
        this.analysisResults = data;
        this.toastr.success('Embryo images and results loaded successfully!', 'Success');
      },
      (error) => {
        this.error = 'Failed to load embryo images and results';
        this.toastr.error('Failed to load embryo images and results.', 'Error');
        console.error('Error fetching data', error);
      }
    );
  }

  validateAndPostForm(embryo: EmbryoImageResult): void {
    this.embryonService.validateAndPostFormData(embryo, this.selectedValues[embryo.image_path], this.notes[embryo.image_path]);
  }
  // validateForm(embryo: EmbryoImageResult): void {
  //   if (!this.selectedValues[embryo.image_path]) {
  //     alert('Please select a value from the dropdown.');
  //   } else if (!this.notes[embryo.image_path]?.trim()) {
  //     alert('Please add a comment.');
  //   } else {
  //     this.postFormData(embryo);
  //   }
  // }

  // postFormData(embryo: EmbryoImageResult): void {
  //   const formData: EmbryoFormData = {
  //     image_path: embryo.image_path,
  //     value: this.selectedValues[embryo.image_path],
  //     note: this.notes[embryo.image_path]
  //   };

  //   this.http.post<any>('http://your-api-endpoint/update', formData).subscribe(
  //     (response) => {
  //       alert('Form data submitted successfully!');
  //       // You can add additional logic here if needed
  //     },
  //     (error) => {
  //       alert('Error submitting form data. Please try again later.');
  //       console.error('Error submitting form data', error);
  //     }
  //   );
  // }

}
