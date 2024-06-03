import { Component } from '@angular/core';
import { ToastrService } from 'ngx-toastr';
import { EmbryoService } from '../embryo.service';
import { FormsModule } from '@angular/forms';
import { ImageUploadService } from '../image-upload.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-analyse-embryon',
  templateUrl: './analyse-embryon.component.html',
  styleUrls: ['./analyse-embryon.component.css']
})
export class AnalyseEmbryonComponent {
  fileErrorMsg: string | null = null;
  analysisResults: any = null;
  selectedFile: File | null = null;

  constructor(private embryoService: EmbryoService, private toastr: ToastrService, private imageUploadService: ImageUploadService, private router: Router) {}

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file = input.files[0];
      const validTypes = ['image/png', 'image/jpeg', 'image/jpg'];
      if (validTypes.includes(file.type)) {
        this.selectedFile = file;
      } else {
        this.toastr.error('Unsupported file format. Please upload a PNG or JPEG image.', 'Error!');
        this.selectedFile = null;
      }
    }
  }

  onSubmit() {
    if (this.selectedFile) {
      const formData = new FormData();
      formData.append('file', this.selectedFile, this.selectedFile.name);

      this.imageUploadService.uploadImage(this.selectedFile).subscribe(
        (response: any) => {
          this.analysisResults = response;
          console.log('Analysis Results:', this.analysisResults);
          this.toastr.success('Your embryo has been successfully analyzed!', 'Success');
          this.router.navigate(['/list']); // Navigate to list
        },
        (error) => {
          console.error('Error:', error);
          this.fileErrorMsg = 'There was an error analyzing the image.';
          this.toastr.error('An error occurred while analyzing your embryo.', 'Error');
        }
      );
    } else {
      this.fileErrorMsg = 'Please select a file first.';
      this.toastr.error('Please ensure all fields are filled correctly.', 'Missing Information!');
    }
  }
}
