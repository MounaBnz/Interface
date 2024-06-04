import { TestBed } from '@angular/core/testing';

import { EmbryonServiceService } from './embryon-service.service';

describe('EmbryonServiceService', () => {
  let service: EmbryonServiceService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(EmbryonServiceService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
